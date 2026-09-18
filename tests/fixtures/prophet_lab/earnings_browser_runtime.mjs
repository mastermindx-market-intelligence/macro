// Browser behavior contract; actual Chromium proof is recorded separately.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const input=JSON.parse(fs.readFileSync(0,'utf8'));
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this.dataset={};this.attributes={};this.hidden=false;this.value='';this._text='';}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(c=>c.textContent).join(' ');}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this._text='';this.children=[...nodes];}
  setAttribute(k,v){this.attributes[k]=String(v);}
  getAttribute(k){return this.attributes[k]??null;}
  removeAttribute(k){delete this.attributes[k];}
  addEventListener(k,fn){(this.listeners[k]??=[]).push(fn);}
  emit(k,event={}){for(const fn of this.listeners[k]||[])fn({...event,preventDefault(){}});}
  querySelectorAll(selector){return this.children.flatMap(c=>[...(selector===c.tag?[c]:[]),...c.querySelectorAll(selector)]);}
}
const controls=Object.fromEntries(['results','detail','status','query','next','first','signin','controls','search','refresh'].map(k=>[k,new Element()]));
const root=new Element('details');root.open=false;
root.querySelector=s=>controls[s.slice(9,-1)];
const doc=new Element();doc.readyState='complete';doc.hidden=false;
doc.documentElement=new Element('html');doc.documentElement.setAttribute('data-lang','en');
doc.createElement=tag=>new Element(tag);doc.querySelectorAll=()=>[root];
const win=new Element();let session={access_token:'private-test-session-token',user:{id:'fixture-user'}};
let authResolve=null,fetchResolve=null,opened=0,observer=null,mode='normal';
const requests=[],timers=new Map();let timerId=0;
win.MDXAuth={client:async()=>({auth:{getSession:()=>mode==='authwait'?new Promise(r=>{authResolve=r;}):Promise.resolve({data:{session}})}}),open:()=>opened++};
const clone=x=>structuredClone(x);
const response=(data,status=200,type='application/json')=>({status,ok:status===200,headers:{get:()=>type},text:async()=>JSON.stringify(data)});
function answer(url){
  const u=new URL(url,'https://prophet.test'),isView=u.pathname.endsWith('/research-view');
  if(mode.startsWith('http'))return response({},Number(mode.slice(4)));
  if(mode==='nonjson')return response({},200,'text/html');
  if(mode==='oversize')return {...response({}),text:async()=> ' '.repeat(1048577)};
  let data;
  if(isView){data=clone(input.view[u.searchParams.get('language')||'en']);if(mode==='wrongref')data.episode_ref.generation_id='peg:'+'f'.repeat(64);}
  else{
    data=clone(input.directory);const q=u.searchParams.get('q')||'',offset=Number(u.searchParams.get('offset')||0);
    let all=data.episodes;if(q)all=all.filter(r=>r.security_id.toLowerCase().includes(q.toLowerCase()));
    data.selection={...data.selection,query:q,offset,limit:25,total_matches:all.length,next_offset:offset+25<all.length?offset+25:null};data.episodes=all.slice(offset,offset+25);
    if(mode==='wronglink')data.episodes[0].research_view_url='https://other.test/collect';
    if(mode==='rank')data.authority.can_rank=true;
    if(mode==='changed_generation'){data.generation_id='peg:'+'b'.repeat(64);for(const row of data.episodes){row.episode_ref.generation_id=data.generation_id;const u=new URL(row.research_view_url,'https://prophet.test');u.searchParams.set('expected_generation',data.generation_id);row.research_view_url=u.pathname+u.search;}}
  }
  return response(data);
}
const context={window:win,document:doc,location:{origin:'https://prophet.test'},URL,URLSearchParams,AbortController,Set,Promise,
  MutationObserver:class{constructor(fn){observer=fn;}observe(){}},
  setTimeout:fn=>{timers.set(++timerId,fn);return timerId;},clearTimeout:id=>timers.delete(id),
  fetch:(url,opts)=>{requests.push({url,opts});if(mode==='wait')return new Promise(r=>{fetchResolve=()=>r(answer(url));});return Promise.resolve(answer(url));}};
vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'),context,{timeout:2000});
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const open=async()=>{root.open=true;root.emit('toggle');await flush();};
const choose=async()=>{const b=controls.results.querySelectorAll('button')[0];assert.ok(b,'directory needs a row');b.emit('click');await flush();};
const noEvidence=()=>{assert.equal(controls.results.children.length,0);assert.equal(controls.detail.children.length,0);};
const signout=()=>win.emit('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}});
const scenario=input.scenario;
assert.equal(requests.length,0,'closed drawer must not read');
if(scenario==='signin_recovery'){session=null;await open();assert.equal(requests.length,0);assert.match(controls.status.textContent,/Sign in/);controls.query.value='UNSUBMITTED';session={access_token:'local-resumed-fixture',user:{id:'fixture-user'}};win.emit('mdx-auth',{detail:{user:session.user,event:'SIGNED_IN'}});await flush();assert.equal(controls.results.querySelectorAll('button').length,25,'successful sign-in must resume the pending open drawer');assert.equal(requests.length,1);assert.equal(controls.query.value,'');}
else if(scenario==='expired_signin_recovery'){await open();mode='http401';await choose();noEvidence();assert.match(controls.status.textContent,/Sign in/);mode='normal';win.emit('mdx-auth',{detail:{user:session.user,event:'SIGNED_IN'}});await flush();assert.equal(controls.results.querySelectorAll('button').length,25);assert.equal(requests.length,3);}
else if(scenario==='signin_closed'){session=null;await open();root.open=false;root.emit('toggle');session={access_token:'local-resumed-fixture',user:{id:'fixture-user'}};win.emit('mdx-auth',{detail:{user:session.user,event:'SIGNED_IN'}});await flush();noEvidence();assert.equal(requests.length,0);}
else if(scenario==='signin_repeat'){await open();await choose();win.emit('mdx-auth',{detail:{user:session.user,event:'SIGNED_IN'}});await flush();assert.equal(requests.length,2);assert.match(controls.detail.textContent,/Earnings evidence/);}
else if(scenario==='signin_forbidden'){await open();mode='http403';await choose();noEvidence();mode='normal';win.emit('mdx-auth',{detail:{user:session.user,event:'SIGNED_IN'}});await flush();noEvidence();assert.equal(requests.length,2);assert.match(controls.status.textContent,/cannot access/);}
else if(scenario==='anonymous'){session=null;await open();assert.equal(requests.length,0);noEvidence();assert.match(controls.status.textContent,/Sign in/);controls.signin.emit('click');assert.equal(opened,1);}
else if(scenario==='absent_auth'){delete win.MDXAuth;await open();assert.equal(requests.length,0);noEvidence();}
else if(scenario==='auth_race'){mode='authwait';await open();signout();authResolve({data:{session}});await flush();assert.equal(requests.length,0);noEvidence();}
else if(scenario==='timeout'){mode='wait';await open();for(const fn of [...timers.values()])fn();await flush();assert.match(controls.status.textContent,/timed out/);noEvidence();}
else if(scenario==='late_response'){mode='wait';await open();const release=fetchResolve;root.open=false;root.emit('toggle');mode='normal';release();await flush();noEvidence();}
else if(['wronglink','rank','nonjson','oversize'].includes(scenario)){mode=scenario;await open();noEvidence();assert.match(controls.status.textContent,/could not be verified/);assert.equal(requests.length,1);}
else{
  await open();assert.equal(controls.results.querySelectorAll('button').length,25,'bounded first page');
  if(scenario==='search'){controls.query.value='NO-SUCH-SECURITY';controls.search.emit('submit');await flush();assert.match(controls.status.textContent,/No recorded opportunities/);assert.equal(controls.results.children.length,0);assert.equal(new URL(requests.at(-1).url,'https://prophet.test').searchParams.get('q'),'NO-SUCH-SECURITY');}
  else if(scenario==='pagination'){controls.next.emit('click');await flush();assert.equal(controls.results.querySelectorAll('button').length,2);assert.equal(new URL(requests.at(-1).url,'https://prophet.test').searchParams.get('expected_generation'),input.directory.generation_id);}
  else if(scenario==='unsubmitted_pagination'){controls.query.value='NO-SUCH-SECURITY';controls.next.emit('click');await flush();assert.equal(new URL(requests.at(-1).url,'https://prophet.test').searchParams.get('q'),'');assert.equal(controls.results.querySelectorAll('button').length,2);assert.equal(controls.query.value,'NO-SUCH-SECURITY');}
  else if(scenario==='unsubmitted_first'){controls.next.emit('click');await flush();controls.query.value='NO-SUCH-SECURITY';controls.first.emit('click');await flush();assert.equal(new URL(requests.at(-1).url,'https://prophet.test').searchParams.get('q'),'');assert.equal(controls.results.querySelectorAll('button').length,25);assert.equal(controls.query.value,'NO-SUCH-SECURITY');}
  else if(scenario==='first_generation'){controls.next.emit('click');await flush();controls.first.emit('click');await flush();assert.equal(new URL(requests.at(-1).url,'https://prophet.test').searchParams.get('expected_generation'),input.directory.generation_id);}
  else if(scenario==='changed_first_generation'){controls.next.emit('click');await flush();mode='changed_generation';controls.first.emit('click');await flush();noEvidence();assert.match(controls.status.textContent,/source version changed/);}
  else if(scenario==='distinct_episodes'){const buttons=controls.results.querySelectorAll('button');assert.notEqual(buttons[0].dataset.episode,buttons[1].dataset.episode);assert.equal(buttons[0].children[0].textContent,buttons[1].children[0].textContent);}
  else if(scenario==='wrongref'){mode=scenario;await choose();noEvidence();assert.match(controls.status.textContent,/could not be verified/);}
  else if(scenario.startsWith('http')){mode=scenario;await choose();noEvidence();const code=Number(scenario.slice(4));assert.match(controls.status.textContent,code===409?/source version changed/:code===401?/Sign in/:[402,403].includes(code)?/cannot access/:/unavailable/);}
  else if(scenario==='late_account_response'){mode='wait';await choose();const release=fetchResolve;signout();mode='normal';release();await flush();noEvidence();}
  else if(scenario==='superseded_response'){mode='wait';await choose();const release=fetchResolve;mode='normal';controls.refresh.emit('click');await flush();release();await flush();assert.ok(!controls.detail.textContent.includes('109,417,000,000'));assert.equal(controls.results.querySelectorAll('button').length,25);}
  else if(scenario==='unsubmitted_input'){mode='wait';controls.refresh.emit('click');await flush();const release=fetchResolve;controls.query.value='UNSUBMITTED';mode='normal';release();await flush();assert.equal(controls.results.querySelectorAll('button').length,25);}
  else if(scenario==='language'){doc.documentElement.setAttribute('data-lang','zh');observer();await flush();await choose();assert.match(controls.detail.textContent,/财报证据/);}
  else{
    await choose();assert.match(controls.detail.textContent,/Earnings evidence/);assert.match(controls.detail.textContent,/109,417,000,000/);
    assert.ok(!controls.detail.textContent.includes('private-test-session-token'));
    if(scenario==='close'){root.open=false;root.emit('toggle');noEvidence();}
    if(scenario==='signout'){signout();noEvidence();}
    if(scenario==='account_change'){win.emit('mdx-auth',{detail:{user:{id:'other-user'},event:'SIGNED_IN'}});noEvidence();}
    if(scenario==='hidden'){doc.hidden=true;doc.emit('visibilitychange');noEvidence();}
    if(scenario==='pagehide'){win.emit('pagehide');noEvidence();}
    if(scenario==='user_updated'){win.emit('mdx-auth',{detail:{user:{id:'fixture-user'},event:'USER_UPDATED'}});noEvidence();}
    if(scenario==='token_refresh'){win.emit('mdx-auth',{detail:{user:{id:'fixture-user'},event:'TOKEN_REFRESHED'}});assert.match(controls.detail.textContent,/Earnings evidence/);assert.equal(requests.length,2);}
  }
}
for(const r of requests){assert.equal(r.opts.cache,'no-store');assert.equal(r.opts.redirect,'error');assert.equal(r.opts.credentials,'same-origin');assert.ok(r.opts.signal);assert.ok(r.opts.headers.Authorization);assert.ok(r.url.startsWith('/api/prophet/lab/v1/episodes'));}
process.stdout.write(JSON.stringify({scenario,status:'PASS',requests:requests.length}));
