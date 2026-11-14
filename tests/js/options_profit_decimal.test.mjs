/** Whole native controllers with controlled DOM/clipboard boundaries; not browser proof.
 * node --test tests/js/options_profit_decimal.test.mjs
 * OPTIONS_PROFIT_ROOT=/path/to/source node --test tests/js/options_profit_decimal.test.mjs
 */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import test from 'node:test';
import vm from 'node:vm';
const ROOT=process.env.OPTIONS_PROFIT_ROOT||join(dirname(fileURLToPath(import.meta.url)),'../..');
const paths=['templates/calculators/options_profit.html.j2','site/tools/calculators/options-profit.html'];
function controller(path){
 const matches=[...readFileSync(join(ROOT,path),'utf8').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].filter(x=>x[1].includes('options-profit self-check'));
 assert.equal(matches.length,1);return matches[0][1];
}
function load(path,{legacy=false,bigint=true}={}){
 const elements=new Map(),events={},writes=[],errors=[];
 function el(id){if(elements.has(id))return elements.get(id);const listeners={},classes=new Set();
 const e={value:'',textContent:'',className:'',listeners,addEventListener(k,f){listeners[k]=f;},
 classList:{add(k){classes.add(k);},remove(k){classes.delete(k);},toggle(k,on){on?classes.add(k):classes.delete(k);}},
 setAttribute(){},getAttribute(k){return k==='data-v'?id:null;},select(){}};elements.set(id,e);return e;}
 const types=[el('call'),el('put')],sides=[el('long'),el('short')];
 el('seg-type').querySelectorAll=()=>types;el('seg-pos').querySelectorAll=()=>sides;let textarea;
 const document={getElementById:el,addEventListener(k,f){events[k]=f;},createElement(){textarea=el('textarea');return textarea;},
 body:{appendChild(){},removeChild(){}},execCommand(){writes.push(textarea.value);return true;}};
 const context=vm.createContext({document,console:{error(...x){errors.push(x);}},BigInt:bigint?BigInt:undefined,
 navigator:legacy?{}:{clipboard:{writeText(s){writes.push(s);return Promise.resolve();}}},setTimeout(){return 1;}});
 const src=controller(path);vm.runInContext(src,context);events.DOMContentLoaded();
 const begin=src.indexOf('  function compute(inp){'),end=src.indexOf('\n  // ── §6 self-check',begin);
 assert.ok(begin>=0&&end>begin);const pure=vm.runInNewContext(src.slice(begin,end)+';compute',{BigInt:bigint?BigInt:undefined});
 return {el,writes,errors,pure,set({type='call',pos='long',K=100,prem=3.1,nC=1,S=103.1}={}){
 for(const [id,value] of Object.entries({strike:K,prem,contracts:nC,spot:S}))el(id).value=String(value);
 el(type).listeners.click();el(pos).listeners.click();},copy(){el('copy-result').listeners.click();},input(id,value){el(id).value=String(value);el(id).listeners.input();}};
}
for(const path of paths){
 test(`${path}: native self-checks and worked example`,()=>{const h=load(path);assert.deepEqual(h.errors,[]);h.set({prem:3,S:110});assert.equal(h.el('out-main').textContent,'+$700.00');assert.match(h.el('out-plain').textContent,/makes \$700\.00/);h.copy();assert.match(h.writes[0],/\+233\.3%/);});
 for(const type of ['call','put'])for(const pos of ['long','short']){
  test(`${path}: ${pos} ${type} exact decimal break-even is neutral in screen and copy`,()=>{
   for(const legacy of [false,true]){const h=load(path,{legacy});const S=type==='call'?103.1:96.9;h.set({type,pos,S});
    const r=h.pure({type,pos,K:100,prem:3.1,nC:1,S});assert.equal(Object.is(r.perShare,0),true);assert.equal(Object.is(r.pl,0),true);assert.equal(Object.is(r.returnPct,0),true);
    assert.equal(h.el('out-main').textContent,'$0.00');assert.equal(h.el('out-main').className,'');assert.equal(h.el('out-ret').textContent,'0.0%');
    assert.match(h.el('out-plain').textContent,/breaks even exactly at expiration/);h.copy();assert.match(h.writes[0],/P\/L at expiration: \$0\.00/);assert.doesNotMatch(h.writes[0],/[-+]\$0\.00|[-+]0\.0%/);
   }
  });
  test(`${path}: ${pos} ${type} genuine cent and sub-cent neighbors retain sign`,()=>{
   const h=load(path);
   for(const [S,per] of (type==='call'?[[103.09,-.01],[103.11,.01],[103.09999999999998,-2e-14],[103.10000000000001,1e-14]]:[[96.89,.01],[96.91,-.01],[96.89999999999999,1e-14],[96.90000000000002,-2e-14]])){
    const want=per*(pos==='long'?1:-1);h.set({type,pos,S});const r=h.pure({type,pos,K:100,prem:3.1,nC:1,S});assert.equal(r.perShare,want);assert.equal(Math.sign(r.pl),Math.sign(want));
    assert.doesNotMatch(h.el('out-plain').textContent,/breaks even/);assert.equal(h.el('out-main').className,want>0?'pos':'neg');
   }
  });
 }
 test(`${path}: repeated side/type/input transitions preserve current neutral result`,()=>{
  const h=load(path);for(let i=0;i<4;i++){h.set({prem:3,S:110});assert.match(h.el('out-main').textContent,/700/);h.set({type:'put',pos:'short',S:96.9});assert.match(h.el('out-plain').textContent,/breaks even/);h.copy();assert.match(h.writes.at(-1),/^Short put P\/L at expiration: \$0\.00/);
  h.input('strike','');h.copy();assert.equal(h.el('out-main').textContent,'—');h.input('strike',100);assert.match(h.el('out-plain').textContent,/breaks even/);}
 });
 test(`${path}: scientific notation and large cancellation`,()=>{
  const h=load(path);for(const [K,prem,S,want]of [[1e-7,3e-9,1.03e-7,0],[1e20,1,1e20,-1],[1e20,20000,1.0000000000000002e20,0],[1e-300,3e-302,1.03e-300,0],[100,3.1,103.11,.01]]){
   assert.equal(h.pure({type:'call',pos:'long',K,prem,nC:1,S}).perShare,want);
  }
 });
 test(`${path}: nonzero decimal payoff below Number range refuses before scaling`,()=>{
  const h=load(path);
  for(const pos of ['long','short'])for(const nC of [1,1000000]){
   const r=h.pure({type:'call',pos,K:1e-308,prem:5e-324,nC,S:1.0000000000000004e-308});
   assert.equal(r.ok,false);assert.match(r.msg,/numeric range/);
  }
 });
 test(`${path}: smallest representable payoff remains nonzero`,()=>{
  const h=load(path);
  for(const pos of ['long','short']){
   const r=h.pure({type:'call',pos,K:1e-308,prem:5e-324,nC:1,S:1e-308});
   assert.equal(r.ok,true);assert.equal(r.perShare,pos==='long'?-5e-324:5e-324);
  }
 });
 test(`${path}: underflow clears prior result and copy then correction recovers`,()=>{
  for(const legacy of [false,true])for(const pos of ['long','short']){
   const h=load(path,{legacy});h.set({prem:3,S:110});h.copy();const before=h.writes.length;
   h.set({pos,K:1e-308,prem:5e-324,nC:1000000,S:1.0000000000000004e-308});
   assert.equal(h.el('out-main').textContent,'—');assert.match(h.el('out-plain').textContent,/numeric range/);
   h.copy();assert.equal(h.writes.length,before);
   h.set();h.copy();assert.match(h.writes.at(-1),/P\/L at expiration: \$0\.00/);
  }
 });
 test(`${path}: expiration-zero, scaling and capped/unlimited controls`,()=>{
  const h=load(path);for(const type of ['call','put'])for(const pos of ['long','short']){
   const r=h.pure({type,pos,K:100,prem:3,nC:2,S:0});assert.equal(r.pl,(type==='call'?-600:19400)*(pos==='long'?1:-1));
   assert.equal(r.profitCapped,pos==='short'||type==='put');assert.equal(r.lossCapped,pos==='long'||type==='put');
  }
 });
 test(`${path}: invalid inputs refuse and correction recovers`,()=>{
  const h=load(path);for(const [id,value]of [['strike',''],['prem',0],['contracts',0],['spot',-1],['spot','1e309']]){h.set();h.input(id,value);const n=h.writes.length;h.copy();assert.equal(h.writes.length,n);assert.equal(h.el('out-main').textContent,'—');h.set();assert.match(h.el('out-plain').textContent,/breaks even/);}
  h.set({type:'put',prem:100,S:0});assert.equal(h.el('out-main').textContent,'—');
 });
 test(`${path}: unsupported BigInt fails explicitly without throwing or copy`,()=>{const h=load(path,{bigint:false});h.set();h.copy();assert.equal(h.el('out-main').textContent,'—');assert.match(h.el('out-plain').textContent,/BigInt support/);assert.equal(h.writes.length,0);});
 test(`${path}: finite direct-input guard precedes decimal conversion`,()=>{const h=load(path);for(const key of ['K','prem','nC','S']){const r=h.pure({type:'call',pos:'long',K:100,prem:3,nC:1,S:110,[key]:Infinity});assert.equal(r.ok,false);}});
}
test('paired complete controllers are identical',()=>assert.equal(controller(paths[0]),controller(paths[1])));
