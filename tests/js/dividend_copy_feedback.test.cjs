/*
 * Dividend copy-only regression. No third-party dependencies or browser launch.
 * Executes the complete authentic template/generated inline controller with a
 * deterministic DOM/event/clipboard/timer adapter, not copied financial helpers.
 * Real browser rendering, native clipboard permissions and OS writes are separate.
 * Run: node --test tests/js/dividend_copy_feedback.test.cjs
 * Optional DIVIDEND_SOURCE_ROOT points at an isolated source snapshot.
 */
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const ROOT = process.env.DIVIDEND_SOURCE_ROOT || path.resolve(__dirname, '../..');
const paths = ['templates/calculators/dividend.html.j2','site/tools/calculators/dividend.html'];
const sources = paths.map(file => ({file, text:readFileSync(path.join(ROOT,file),'utf8')}));
function script(text){
 const found=[...text.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(s=>s.includes('dividend self-check'));
 assert.equal(found.length,1,'one complete Dividend controller');return found[0];
}
const OUTPUTS=['out-main','out-yield','out-monthly','out-shares','out-projincome','out-projvalue'];
const BASE={amount:'10,000',price:'50',dps:'2',growth:'0',years:''};
const PAYLOAD='Dividend income: $400.00/yr ($33.33/mo) at a 4.00% yield on 200 shares — mastermind-x.com';
const flush=async()=>{for(let i=0;i<6;i++)await Promise.resolve();};
function mount(source,{api='success',legacy=false}={}){
 const nodes=new Map(),writes=[],legacyWrites=[],errors=[],timers=new Map(),effects=[];
 let active=null, timerId=0, temporary=0;
 function element(id,tag='div'){
  const classes=new Set(),listeners={};
  return {id,tagName:tag.toUpperCase(),value:'',textContent:'',hidden:false,rows:4,scrollTop:0,selectionStart:0,selectionEnd:0,attrs:{},listeners,
   classList:{add(v){classes.add(v)},remove(v){classes.delete(v)},contains(v){return classes.has(v)},toggle(v,on){if(on??!classes.has(v))classes.add(v);else classes.delete(v)}},
   setAttribute(k,v){this.attrs[k]=String(v)},getAttribute(k){return this.attrs[k]??null},removeAttribute(k){delete this.attrs[k]},
   addEventListener(kind,fn){(listeners[kind]??=[]).push(fn)},fire(kind,event={}){for(const fn of listeners[kind]||[])fn(event)},
   focus(){active=this;effects.push('focus:'+id)},select(){active=this;this.selectionStart=0;this.selectionEnd=this.value.length;effects.push('select:'+id)},
   scrollIntoView(){effects.push('scroll:'+id)},get clientHeight(){return this.rows*20},get scrollHeight(){return Math.ceil(this.value.length/60)*20},
   querySelectorAll(){return []}};
 }
 for(const match of source.matchAll(/<([a-z][a-z0-9]*)\b([^>]*\bid="([^"]+)"[^>]*)>/gi)){
  const el=element(match[3],match[1]);el.hidden=/\bhidden(?:\s|=|$)/.test(match[2]);nodes.set(el.id,el);
 }
 const get=id=>{const e=nodes.get(id);assert.ok(e,'actual source declares #'+id);return e;};
 const buttons=['reinvest','cash'].map(v=>{const b=element(v,'button');b.setAttribute('data-v',v);return b;});
 const seg=element('mode');seg.querySelectorAll=()=>buttons;
 const docListeners={},children=[];
 const document={getElementById:id=>nodes.get(id)||null,querySelector(selector){assert.equal(selector,'.ci-seg[data-name="mode"]');return seg;},
  addEventListener(k,fn){(docListeners[k]??=[]).push(fn)},createElement(tag){return element('temporary-'+(++temporary),tag)},
  body:{appendChild(e){children.push(e);effects.push('append')},removeChild(e){assert.ok(children.includes(e));children.splice(children.indexOf(e),1);effects.push('remove')}},
  execCommand(command){assert.equal(command,'copy');assert.equal(children.length,1);legacyWrites.push(children[0].value);if(legacy==='throw')throw new Error('controlled legacy denial');return legacy;}};
 const navigator={};
 if(api!=='absent')navigator.clipboard={writeText(text){
  const item={text};writes.push(item);
  if(api==='throw')throw new Error('controlled synchronous denial');
  if(api==='reject')return Promise.reject(new Error('controlled async denial'));
  if(api==='deferred')return new Promise((resolve,reject)=>{item.resolve=resolve;item.reject=reject});
  return Promise.resolve();
 }};
 const context={document,navigator,Promise,console:{error:(...a)=>errors.push(a)},
  setTimeout(fn,delay){const id=++timerId;timers.set(id,{fn,delay,canceled:false});return id},
  clearTimeout(id){assert.ok(timers.has(id));timers.get(id).canceled=true;}};
 vm.runInNewContext(script(source),context,{timeout:1000});
 for(const fn of docListeners.DOMContentLoaded||[])fn();
 return {get,nodes,writes,legacyWrites,errors,timers,effects,children,
  set(values){for(const[id,v]of Object.entries(values))get(id).value=String(v);get('amount').fire('input')},
  input(id,value){get(id).value=String(value);get(id).fire('input')},
  valid(){this.set(BASE)},mode(value){const b=buttons.find(b=>b.getAttribute('data-v')===value);assert.ok(b);seg.fire('click',{target:{closest:()=>b}})},
  lang(){for(const fn of docListeners.langchange||[])fn()},
  async copy(){get('copy-result').fire('click');await flush()},
  async resolve(index=0){writes[index].resolve();await flush()},async reject(index=0){writes[index].reject(new Error('controlled deferred denial'));await flush()},
  fireTimer(id){timers.get(id).fn()},get active(){return active},
  get copied(){return get('copied').classList.contains('show')},get fallback(){return nodes.get('copy-fallback')},get recovery(){return nodes.get('copy-fallback-text')},
  snapshot(){return Object.fromEntries([...OUTPUTS,'out-plain'].map(id=>[id,get(id).textContent]))}};
}
function noFeedback(a){assert.equal(a.copied,false);assert.equal(a.fallback?.hidden??true,true);assert.equal(a.recovery?.value??'','');}
function fallback(a,text=PAYLOAD){
 assert.equal(a.copied,false,'failed copy must not say Copied');
 assert.ok(a.fallback,'recoverable failure markup exists');assert.equal(a.fallback.hidden,false);
 assert.equal(a.recovery.value,text);assert.equal(a.recovery.selectionStart,0);assert.equal(a.recovery.selectionEnd,text.length);
 assert.equal(a.active,a.recovery);assert.equal(a.recovery.scrollTop,0);assert.equal(a.children.length,0,'temporary legacy node removed');
}
function scenario(name,run){for(const s of sources)test(s.file+': '+name,async()=>run(mount,s));}

test('template and generated controller bodies match',()=>assert.equal(script(sources[0].text),script(sources[1].text)));
scenario('canonical self-checks and initial empty form remain sound',async(m,s)=>{const a=m(s.text);assert.deepEqual(a.errors,[]);assert.ok(OUTPUTS.every(id=>a.get(id).textContent==='—'));await a.copy();assert.equal(a.writes.length,0);noFeedback(a)});
scenario('ordinary base income and copy payload remain byte-stable',async(m,s)=>{const a=m(s.text);a.valid();assert.equal(a.get('out-main').textContent,'$400.00');assert.equal(a.get('out-monthly').textContent,'$33.33');assert.equal(a.get('out-yield').textContent,'4.00%');assert.equal(a.get('out-shares').textContent,'200');await a.copy();assert.equal(a.writes[0].text,PAYLOAD);assert.equal(a.copied,true);assert.equal(a.legacyWrites.length,0)});
scenario('both projection modes and copy values stay unchanged',async(m,s)=>{const a=m(s.text);a.valid();a.input('years','1');assert.equal(a.get('out-projincome').textContent,'$416.00');assert.equal(a.get('out-projvalue').textContent,'$10,400.00');await a.copy();assert.match(a.writes.at(-1).text,/after 1y reinvested: \$416\.00\/yr/);a.mode('cash');assert.equal(a.get('out-projincome').textContent,'$400.00');assert.equal(a.get('out-projvalue').textContent,'$10,400.00');await a.copy();assert.match(a.writes.at(-1).text,/after 1y cash: \$400\.00\/yr/)});
for(const api of ['reject','throw','absent']){
 for(const legacy of [false,'throw'])scenario(api+' with legacy '+legacy+' gives selected recovery, not success',async(m,s)=>{const a=m(s.text,{api,legacy});a.valid();await a.copy();fallback(a);assert.equal(a.legacyWrites.length,1);assert.deepEqual(a.errors,[])});
 scenario(api+' preserves successful legacy copy',async(m,s)=>{const a=m(s.text,{api,legacy:true});a.valid();await a.copy();assert.equal(a.copied,true);assert.equal(a.legacyWrites[0],PAYLOAD);assert.equal(a.fallback?.hidden??true,true);assert.equal(a.children.length,0)});
}
scenario('legacy nonboolean truthy result is not acknowledged',async(m,s)=>{const a=m(s.text,{api:'absent',legacy:'true'});a.valid();await a.copy();fallback(a)});
scenario('required input invalidation clears feedback and copy eligibility',async(m,s)=>{const a=m(s.text);a.valid();await a.copy();a.input('amount','');noFeedback(a);assert.ok(OUTPUTS.every(id=>a.get(id).textContent==='—'));await a.copy();assert.equal(a.writes.length,1);a.valid();assert.equal(a.get('out-main').textContent,'$400.00')});
for(const input of ['amount','price','dps','growth','years'])scenario(input+' edit invalidates pending success',async(m,s)=>{const a=m(s.text,{api:'deferred'});a.valid();await a.copy();a.input(input,input==='years'?'1':'3');await a.resolve();noFeedback(a)});
for(const change of ['input','mode','language']){
 scenario(change+' clears displayed success and its timeout',async(m,s)=>{const a=m(s.text);a.valid();await a.copy();const t=[...a.timers.keys()].at(-1);if(change==='input')a.input('amount','20000');else if(change==='mode')a.mode('cash');else a.lang();noFeedback(a);assert.equal(a.timers.get(t).canceled,true);a.fireTimer(t);noFeedback(a)});
 scenario(change+' makes old rejection inert before legacy/focus effects',async(m,s)=>{const a=m(s.text,{api:'deferred',legacy:true});a.valid();await a.copy();if(change==='input')a.input('amount','20000');else if(change==='mode')a.mode('cash');else a.lang();const before=a.effects.length;await a.reject();assert.equal(a.legacyWrites.length,0);assert.equal(a.effects.length,before);noFeedback(a)});
 scenario(change+' removes stale selected recovery text',async(m,s)=>{const a=m(s.text,{api:'reject',legacy:false});a.valid();await a.copy();fallback(a);if(change==='input')a.input('amount','20000');else if(change==='mode')a.mode('cash');else a.lang();noFeedback(a)});
}
scenario('old rejected attempt cannot overwrite newer success',async(m,s)=>{const a=m(s.text,{api:'deferred',legacy:true});a.valid();await a.copy();await a.copy();await a.resolve(1);assert.equal(a.copied,true);await a.reject(0);assert.equal(a.copied,true);assert.equal(a.legacyWrites.length,0);assert.equal(a.fallback?.hidden??true,true)});
scenario('old success cannot overwrite newer recovery',async(m,s)=>{const a=m(s.text,{api:'deferred',legacy:false});a.valid();await a.copy();a.input('amount','20000');await a.copy();await a.reject(1);fallback(a,a.writes[1].text);await a.resolve(0);fallback(a,a.writes[1].text)});
scenario('latest rejection may still use successful legacy fallback',async(m,s)=>{const a=m(s.text,{api:'deferred',legacy:true});a.valid();await a.copy();await a.reject();assert.equal(a.legacyWrites[0],PAYLOAD);assert.equal(a.copied,true)});
scenario('new attempt clears prior recovery while pending',async(m,s)=>{const a=m(s.text,{api:'deferred',legacy:false});a.valid();await a.copy();await a.reject();fallback(a);await a.copy();noFeedback(a);await a.resolve(1);assert.equal(a.copied,true)});
scenario('old timeout cannot remove newer success',async(m,s)=>{const a=m(s.text);a.valid();await a.copy();const old=[...a.timers.keys()].at(-1);await a.copy();assert.equal(a.copied,true);assert.equal(a.timers.get(old).canceled,true);a.fireTimer(old);assert.equal(a.copied,true);const latest=[...a.timers.keys()].at(-1);assert.equal(a.timers.get(latest).delay,1600);a.fireTimer(latest);assert.equal(a.copied,false)});
scenario('clearing all inputs resets results and copy eligibility',async(m,s)=>{const a=m(s.text);a.valid();await a.copy();a.set({amount:'',price:'',dps:'',growth:'',years:''});noFeedback(a);assert.ok(OUTPUTS.every(id=>a.get(id).textContent==='—'));await a.copy();assert.equal(a.writes.length,1)});
scenario('fallback uses existing bilingual labels and readonly selection control',async(m,s)=>{assert.ok(/Could not copy automatically\./.test(s.text),'English recovery explanation');assert.ok(/未能自动复制。下方文字已选中/.test(s.text),'Chinese recovery explanation');assert.ok(/for="copy-fallback-text"/.test(s.text),'label identifies recovery control');assert.ok(/id="copy-fallback-text" readonly rows="4" spellcheck="false"/.test(s.text),'readonly selection control');if(s.file.endsWith('.j2'))assert.ok(/t\('Could not copy automatically\./.test(s.text),'template translation macro');else assert.ok(/class="l-zh">未能自动复制/.test(s.text),'generated translation span')});
