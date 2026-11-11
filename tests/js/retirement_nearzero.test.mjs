import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const path=process.argv[2];
const s=fs.readFileSync(path,'utf8');
const controller=s.match(/\(function\(\)\{\s*"use strict";[\s\S]*?\n\}\)\(\);/)[0];
const compute=vm.runInNewContext('('+controller.match(/  function compute\(inp\)\{[\s\S]*?\n  \}/)[0]+')');
let pass=0,fail=0;const failures=[];
function test(name,fn){try{fn();pass++;}catch(e){fail++;failures.push({name,error:e.message});}}
function close(a,b,tol=1e-10){assert(Number.isFinite(a),String(a));assert(Math.abs(a-b)<=tol*Math.max(1,Math.abs(b)),`${a} != ${b}`);}
function mount(){
 const events={},copies=[],errors=[];
 const make=()=>({value:'',textContent:'',className:'',handlers:{},classList:{add(){},remove(){}},addEventListener(n,f){this.handlers[n]=f;},select(){}});
 const ids=Object.fromEntries(['curage','retage','principal','contrib','rate','out-main','out-plain','out-contrib','out-growth','out-years','out-gshare','copy-result','copied'].map(id=>[id,make()]));
 const document={addEventListener:(n,f)=>events[n]=f,getElementById:id=>ids[id],createElement:make,body:{appendChild(){},removeChild(){}},execCommand:()=>true};
 vm.runInNewContext(controller,{document,navigator:{clipboard:{writeText:line=>{copies.push(line);return Promise.resolve();}}},setTimeout:()=>0,console:{error:(...x)=>errors.push(x)}});
 events.DOMContentLoaded();
 const set=(id,v)=>{ids[id].value=String(v);ids[id].handlers.input();};
 return {ids,set,copies,errors,copy:()=>ids['copy-result'].handlers.click()};
}
const ui=mount();
test('existing worked-example self checks',()=>assert.deepEqual(ui.errors,[]));
for(const [id,v] of Object.entries({curage:30,retage:65,principal:10000,contrib:500}))ui.set(id,v);
const rates=[0,1e-14,1e-12,1e-10,1e-100,1e-300,1e-320,Number.MIN_VALUE];
const uiEvidence=[];
for(const rate of rates){
 ui.set('rate',rate);ui.copy();
 uiEvidence.push({rate,out:ui.ids['out-main'].textContent,growth:ui.ids['out-growth'].textContent,share:ui.ids['out-gshare'].textContent,copy:ui.copies.at(-1)});
 test(`entire controller cash-limit rate ${rate}`,()=>{
   assert.equal(ui.ids['out-main'].textContent,'$220,000');
   assert.equal(ui.ids['out-contrib'].textContent,'$220,000');
   assert.equal(ui.ids['out-growth'].textContent,'$0');
   assert(!ui.ids['out-gshare'].textContent.includes('-'));
   assert(ui.copies.at(-1).includes('$220,000 nest egg'));
 });
}
ui.set('rate',6);const ordinary=ui.ids['out-main'].textContent;
// Independently checked by 80-digit Decimal monthly recurrence: 793590.6643181...
test('ordinary whole-controller projection',()=>assert.equal(ordinary,'$793,591'));
ui.set('rate',1e-14);ui.set('rate',6);
test('correction preserves all entered inputs and output',()=>{
 assert.equal(ui.ids['out-main'].textContent,ordinary);
 assert.deepEqual(['curage','retage','principal','contrib'].map(k=>ui.ids[k].value),['30','65','10000','500']);
});
for(const rate of [0,1e-14,1e-12,1e-10,0.01,1,6,12])
 for(const months of [1,2,12,60,420,1200])
  for(const [P,c] of [[0,500],[10000,0],[10000,500]]){
   test(`independent monthly recurrence ${rate}/${months}/${P}/${c}`,()=>{
    let expected=P;const i=rate/100/12;
    for(let k=0;k<months;k++)expected=expected*(1+i)+c;
    const r=compute({cur:0,ret:months/12,P,c,r:rate});assert(r.ok);close(r.fv,expected,2e-10);
    close(r.contributed,P+c*months);assert(r.growth>=-Math.max(1,r.fv)*1e-13);
   });
  }
for(const rate of [6e-321,1e-320,2e-320,1e-318])
 for(const years of [.03125,.0625,.125,.25]){
  test(`subnormal fractional horizon ${rate}/${years}`,()=>{
   const r=compute({cur:0,ret:years,P:10000,c:500,r:rate});assert(r.ok);close(r.fv,10000+500*12*years,1e-14);
  });
 }
for(const [name,inp] of [
 ['equal ages',{cur:30,ret:30,P:10000,c:500,r:6}],
 ['reversed ages',{cur:65,ret:30,P:10000,c:500,r:6}],
 ['negative savings',{cur:30,ret:65,P:-1,c:500,r:6}],
 ['negative contribution',{cur:30,ret:65,P:10000,c:-1,r:6}],
 ['negative return',{cur:30,ret:65,P:10000,c:500,r:-1}],
 ['no funding',{cur:30,ret:65,P:0,c:0,r:6}],
 ['overflow',{cur:0,ret:1e100,P:10000,c:500,r:6}],
 ])test(`preserved invalid boundary ${name}`,()=>assert.equal(compute(inp).ok,false));
let seed=20261104;const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/2**32;};
for(let k=0;k<2000;k++){
 const P=rand()*1e6,c=rand()*1e4,months=1+Math.floor(rand()*840),r=rand()*30;
 test(`deterministic ordinary envelope ${k}`,()=>{
  let expected=P;const i=r/100/12;for(let j=0;j<months;j++)expected=expected*(1+i)+c;
  const got=compute({cur:0,ret:months/12,P,c,r});assert(got.ok);close(got.fv,expected,2e-10);
  assert(got.growth>=0);assert(Object.values(got).filter(x=>typeof x==='number').every(Number.isFinite));
 });
}
console.log(JSON.stringify({path,pass,fail,uiEvidence,failures:failures.slice(0,15)},null,2));
process.exitCode=fail?1:0;
