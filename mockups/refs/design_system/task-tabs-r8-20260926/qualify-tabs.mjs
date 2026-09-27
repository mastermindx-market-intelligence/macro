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
writeFileSync(join(root,'browser-r8-process.json'),JSON.stringify({pid:child.pid,profile,operation:'design-system-r8-tab-qualification-20260926',source:'integrated'}));
try{
 const endpoint=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(new Error('Chrome launch timeout')),15000);child.stderr.on('data',b=>{text+=b.toString();const m=text.match(/DevTools listening on (ws:\/\/\S+)/);if(m){clearTimeout(timer);resolve(m[1]);}});child.on('exit',code=>{if(!text.includes('DevTools listening'))reject(new Error('Chrome exited '+code));});});
 ws=new WebSocket(endpoint);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
 ws.onmessage=event=>{const d=JSON.parse(event.data);if(d.id&&pending.has(d.id)){const p=pending.get(d.id);clearTimeout(p.timer);pending.delete(d.id);d.error?p.reject(new Error(JSON.stringify(d.error))):p.resolve(d.result);}else if(d.method==='Runtime.exceptionThrown')exceptions.push(d.params);else if(d.method==='Page.loadEventFired')loads++;};
 const target=await send('Target.createTarget',{url:'about:blank'},null);session=(await send('Target.attachToTarget',{targetId:target.targetId,flatten:true},null)).sessionId;
 await send('Page.enable');await send('Page.bringToFront');await send('Runtime.enable');await send('Network.enable');await send('Network.setBlockedURLs',{urls:['http://*','https://*']});await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
 for(const width of [320,390,1440])for(const theme of ['dark','light'])for(const lang of ['en','zh']){
  const result={width,theme,lang,checks:[]};const check=(name,pass,detail)=>result.checks.push({name,pass:!!pass,...(detail===undefined?{}:{detail})});
  const url=pathToFileURL(join(root,'integrated/mockups/design_system/specimen.html')).href+'?market=US&period=1w&case='+cells.length+'#tab-fi';
  await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url});await until(`location.href===${JSON.stringify(url)}&&document.readyState==='complete'&&!!document.getElementById('specimen-research-tabs')`);
  async function look(){await evaluate(`(()=>{const r=document.documentElement;if((r.getAttribute('data-theme')||'dark')!==${JSON.stringify(theme)})document.getElementById('t-theme').click();if(r.getAttribute('data-lang')!==${JSON.stringify(lang)})document.getElementById('t-lang').click();return true})()`);await settle();}
  await look();let s=await state();check('direct_filing_link',selected(s,'tab-fi','pane-filings'),s);const search=s.search;
  const storage=await evaluate('JSON.stringify([Object.entries(localStorage),Object.entries(sessionStorage)])');
  await click('tab-pf');s=await state();check('pointer_price_panel',selected(s,'tab-pf','pane-demo')&&s.focus==='tab-pf');
  const scroll=await evaluate(`(()=>{const x=document.querySelector('#pane-demo .mx-tblbox');x.scrollLeft=x.scrollWidth;return x.scrollLeft})()`);const historyBefore=await evaluate('history.length');
  await key('ArrowRight','ArrowRight',39);s=await state();check('arrow_focus_only',s.focus==='tab-fu'&&selected(s,'tab-pf','pane-demo')&&s.hash==='#tab-pf');
  check('arrow_has_no_history_effect',await evaluate('history.length')===historyBefore);
  await key('Enter','Enter',13);await settle();s=await state();check('enter_fundamentals',selected(s,'tab-fu','pane-fundamentals')&&s.hash==='#tab-fu'&&s.focus==='tab-fu');
  check('fundamentals_content_visible',await evaluate(`document.querySelector('#pane-fundamentals .l-${lang}').getBoundingClientRect().height>0&&document.querySelector('#pane-demo').hidden`));
  check('simple_fundamentals_no_sideways_reading',await evaluate("(()=>{const b=document.querySelector('#pane-fundamentals .mx-tblbox');return b.scrollWidth<=b.clientWidth+1})()"));
  await key('Tab','Tab',9);s=await state();check('tab_enters_active_panel',s.focus==='pane-fundamentals');
  await key('Tab','Tab',9,8);s=await state();check('shift_tab_returns_to_selected',s.focus==='tab-fu');
  await key('End','End',35);s=await state();check('end_focus_only',s.focus==='tab-fi'&&selected(s,'tab-fu','pane-fundamentals'));
  await key(' ','Space',32);await settle();s=await state();check('space_filing_panel',selected(s,'tab-fi','pane-filings')&&s.hash==='#tab-fi');
  await evaluate('history.back()');await until("location.hash==='#tab-fu'");await settle();s=await state();check('back_returns_fundamentals',selected(s,'tab-fu','pane-fundamentals')&&s.focus==='tab-fu',s);
  await evaluate('history.forward()');await until("location.hash==='#tab-fi'");await settle();check('forward_returns_filings',selected(await state(),'tab-fi','pane-filings'));
  await evaluate('history.back()');await until("location.hash==='#tab-fu'");await evaluate('history.back()');await until("location.hash==='#tab-pf'");await settle();s=await state();check('back_returns_price',selected(s,'tab-pf','pane-demo'));
  check('table_position_preserved',await evaluate("document.querySelector('#pane-demo .mx-tblbox').scrollLeft")===scroll);
  const repeated=await evaluate('history.length');await click('tab-pf');check('repeat_selection_no_history_entry',await evaluate('history.length')===repeated);
  await key('ArrowLeft','ArrowLeft',37);s=await state();check('left_wraps_focus',s.focus==='tab-fi'&&selected(s,'tab-pf','pane-demo'));
  await key('Home','Home',36);check('home_focus', (await state()).focus==='tab-pf');
  await evaluate("location.hash='specimen-state-actions'");await until("location.hash==='#specimen-state-actions'");await settle();s=await state();check('unrelated_fragment_preserved',s.hash==='#specimen-state-actions'&&selected(s,'tab-pf','pane-demo'));
  await evaluate("location.hash='tab-fu'");await until("document.getElementById('tab-fu').getAttribute('aria-selected')==='true'");await settle();check('external_known_fragment',selected(await state(),'tab-fu','pane-fundamentals'));
  const before=loads;await send('Page.reload');for(let n=0;n<80&&loads<=before;n++)await sleep(50);if(loads<=before)throw new Error('Reload did not complete');await until("document.readyState==='complete'&&!!document.getElementById('pane-fundamentals')");await look();s=await state();check('reload_restores_panel',selected(s,'tab-fu','pane-fundamentals'));
  await click('tab-fi');await evaluate("document.getElementById('pane-filings').focus()");await evaluate('history.back()');await until("location.hash==='#tab-fu'");await settle();s=await state();check('history_never_leaves_focus_in_hidden_panel',selected(s,'tab-fu','pane-fundamentals')&&s.focus==='tab-fu');
  check('query_scope_preserved',s.search===search);check('reciprocal_labels',s.reciprocal);check('document_containment',s.documentWidth<=s.clientWidth+1,s);check('tab_target_geometry',s.tabHeights.every(h=>h>=44)&&s.tabWidths.every(w=>w>=44));
  check('no_storage_effect',storage===await evaluate('JSON.stringify([Object.entries(localStorage),Object.entries(sessionStorage)])'));
  check('locale_matches_document',await evaluate(`document.documentElement.lang===${JSON.stringify(lang==='zh'?'zh-CN':'en')}`));
  if((width===1440&&theme==='dark'&&lang==='en')||(width===390&&theme==='light'&&lang==='zh')){
   await evaluate("document.getElementById('specimen-tabs-title').scrollIntoView({block:'start'});scrollBy(0,-document.querySelector('.bar').getBoundingClientRect().height-20)");await settle();await sleep(200);const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(root,`tabs-${width}-${theme}-${lang}.png`),Buffer.from(shot.data,'base64'));
  }
  result.pass=result.checks.every(x=>x.pass);cells.push(result);console.log('CELL',width,theme,lang,result.pass?'PASS':'FAIL',result.checks.filter(x=>!x.pass).map(x=>x.name));
 }
 const report={scope:'R8 reference tabs on composed current-main source; isolated local file browser; external HTTP(S) blocked; no production, persistence or assistive-technology claim',cells,exceptions};
 writeFileSync(join(root,'browser-tabs-final.json'),JSON.stringify(report,null,2));console.log('FINAL',cells.length,cells.filter(x=>x.pass).length,'CHECKS',cells.reduce((a,c)=>a+c.checks.length,0),'EXCEPTIONS',exceptions.length);
 if(cells.some(x=>!x.pass)||exceptions.length)process.exitCode=1;
 ws.send(JSON.stringify({id:++seq,method:'Browser.close',params:{}}));await sleep(500);
}catch(e){writeFileSync(join(root,'browser-tabs-error.txt'),String(e.stack));console.error(e);process.exitCode=1;}
finally{
 if(ws)ws.close();for(const p of pending.values())clearTimeout(p.timer);pending.clear();
 if(child.exitCode===null&&child.signalCode===null)child.kill('SIGTERM');
 await Promise.race([new Promise(r=>child.once('exit',r)),sleep(1800)]);
 writeFileSync(join(root,'browser-tabs-cleanup.json'),JSON.stringify({pid:child.pid,profile,exitCode:child.exitCode,signalCode:child.signalCode,closed:child.exitCode!==null||child.signalCode!==null}));child.stderr.destroy();child.unref();process.exit(process.exitCode||0);
}
