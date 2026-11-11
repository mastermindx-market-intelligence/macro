import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Runs the actual complete calculator controller, not a reconstructed calculator.
// No browser, shared page scripts, network, permissions or real clipboard are used.
const path=process.argv[2] || 'templates/calculators/savings_goal.html.j2';
const source=fs.readFileSync(path,'utf8');
const controller=source.match(/\(function\(\)\{\s*"use strict";[\s\S]*?\n\}\)\(\);/)[0];
const compute=vm.runInNewContext('('+controller.match(/  function compute\(inp\)\{[\s\S]*?\n  \}/)[0]+')');
let pass=0,fail=0;
function test(name,fn){try{fn();pass++;}catch(e){fail++;console.error('FAIL',name,e.message);}}
function close(actual,expected,tol=1e-9){assert(Number.isFinite(actual));assert(Math.abs(actual-expected)<=tol*Math.max(1,Math.abs(expected)),`${actual} != ${expected}`);}
function mount(){
  const events={},copied=[],errors=[];
  const make=()=>({value:'',textContent:'',className:'',hidden:false,style:{},handlers:{},
    classList:{add(){},remove(){},toggle(){}},addEventListener(n,f){this.handlers[n]=f;},setAttribute(){},select(){}});
  const ids=Object.fromEntries(['goal','current','rate','years','monthly','row-years','row-monthly','out-main','out-unit','out-plain','out-gap','out-contrib','out-growth','out-time','copy-result','copied'].map(id=>[id,make()]));
  const buttons=['date','contrib'].map(mode=>({...make(),getAttribute:n=>n==='data-v'?mode:null,closest(){return this;}}));
  const seg={...make(),querySelectorAll:()=>buttons};
  const document={addEventListener:(n,f)=>events[n]=f,getElementById:id=>ids[id],querySelector:()=>seg,createElement:make,body:{appendChild(){},removeChild(){}},execCommand:()=>true};
  vm.runInNewContext(controller,{document,navigator:{clipboard:{writeText:s=>{copied.push(s);return Promise.resolve();}}},setTimeout:()=>0,console:{error:(...x)=>errors.push(x)}});
  events.DOMContentLoaded();
  const set=(id,v)=>{ids[id].value=String(v);ids[id].handlers.input();};
  const mode=m=>seg.handlers.click({target:buttons[m==='date'?0:1]});
  return {ids,set,mode,copied,errors,copy:()=>ids['copy-result'].handlers.click()};
}
const ui=mount();
test('worked example self checks',()=>assert.deepEqual(ui.errors,[]));
for(const [id,v] of Object.entries({goal:50000,current:5000,years:5,monthly:750})) ui.set(id,v);
for(const r of [0,1e-14,1e-12,1e-10,1e-100,1e-300,1e-320,Number.MIN_VALUE]){
  test(`complete controller near-zero rate ${r}`,()=>{
    ui.set('rate',r);ui.mode('date');assert.equal(ui.ids['out-main'].textContent,'$750');assert.equal(ui.ids['out-growth'].textContent,'$0');
    ui.copy();assert(ui.copied.at(-1).includes('$750.00/mo'));
    ui.mode('contrib');assert(ui.ids['out-main'].textContent.includes('60 mo'));assert.equal(ui.ids['out-growth'].textContent,'$0');
  });
}
test('overflowed finite horizon withholds numbers and copy',()=>{
  ui.mode('date');ui.set('rate',0);ui.set('years','1e308');
  for(const id of ['out-main','out-gap','out-contrib','out-growth','out-time']) assert.equal(ui.ids[id].textContent,'—',id);
  const before=ui.copied.length;ui.copy();assert.equal(ui.copied.length,before);
  ui.set('years',5);assert.equal(ui.ids['out-main'].textContent,'$750');
});
for(const years of ['1e300','1e306','1e307'])test(`full controller finite large horizon ${years}`,()=>{
  ui.mode('date');ui.set('rate',0);ui.set('years',years);
  for(const id of ['out-main','out-gap','out-contrib','out-growth','out-time','out-plain'])assert(!/NaN|Infinity/.test(ui.ids[id].textContent),id);
  ui.copy();assert(!/NaN|Infinity/.test(ui.copied.at(-1)));
});
test('full controller huge finite contribution time',()=>{
  ui.set('goal','1e308');ui.set('current',0);ui.set('monthly',1);ui.mode('contrib');
  assert(!/NaN|Infinity/.test(ui.ids['out-main'].textContent));ui.copy();assert(!/NaN|Infinity/.test(ui.copied.at(-1)));
});
for(const r of [0,1e-300,100])test(`unrepresentable positive deposit refuses r${r}`,()=>{
  assert.equal(compute({G:1e-300,P:0,r,n:1e307,mode:'date'}).ok,false);
});
// Independent power-of-two scaling avoids the overflowing annuity factor.
for(const [m,expected] of [[1025,.24],[1026,.115],[1027,.0525]])test('overflowed growth with a positive required deposit m'+m,()=>{
  const G=2**1023,P=.01,discountedGoal=2**(1023-m);
  const oracle=(discountedGoal-P)/(1-2**(-m));
  close(oracle,expected,1e-14);assert(oracle>0);assert(P/discountedGoal<1);
  assert.equal(compute({G,P,r:1200,n:m/12,mode:'date'}).ok,false);
});
test('finite large growth factor retains a positive contribution',()=>{
  const got=compute({G:2**1023,P:.01,r:1200,n:1023/12,mode:'date'});
  assert(got.ok);close(got.monthly,.99,1e-10);
});
test('overflowed growth withholds actual output and copy, then recovers',()=>{
  const view=mount();
  for(const [id,value] of Object.entries({goal:2**1023,current:.01,rate:1200,years:85.5,monthly:750}))view.set(id,value);
  view.mode('date');
  for(const id of ['out-main','out-gap','out-contrib','out-growth','out-time'])assert.equal(view.ids[id].textContent,'—',id);
  assert.match(view.ids['out-plain'].textContent,/doesn't resolve/);
  const before=view.copied.length;view.copy();assert.equal(view.copied.length,before);
  for(const [id,value] of Object.entries({goal:50000,current:5000,rate:0,years:5}))view.set(id,value);
  assert.equal(view.ids['out-main'].textContent,'$750');view.copy();
  assert(view.copied.at(-1).includes('$750.00/mo'));
});
for(const bad of [NaN,Infinity,-Infinity]) for(const key of ['G','P','r','n','c']) test(`nonfinite ${key} ${bad}`,()=>{
  const inp={G:50000,P:5000,r:6,n:5,c:750,mode:key==='c'?'contrib':'date',[key]:bad};assert.equal(compute(inp).ok,false);
});
for(const n of [.001,.01,.1,.125,.5,1,5,100]) for(const r of [1e-300,1e-319,1e-320]) test(`fractional near-zero n${n} r${r}`,()=>{
  const date=compute({G:50000,P:5000,r,n,mode:'date'});assert(date.ok);close(date.monthly,45000/(n*12));
  const inverse=compute({G:50000,P:5000,r,c:45000/(n*12),mode:'contrib'});assert(inverse.ok);close(inverse.months,n*12);
});
// Independent oracle: month-by-month account accumulation and unit deposits.
for(const P of [0,100,5000]) for(const G of [10000,50000,100000]) for(const m of [12,60,120]) for(const r of [0,1e-14,1e-12,1e-10,.001,1,6,15]) test(`recurrence P${P} G${G} m${m} r${r}`,()=>{
  const i=r/1200;let balance=P,annuity=0;
  for(let k=0;k<m;k++){balance*=1+i;annuity=annuity*(1+i)+1;}
  const expected=Math.max(0,(G-balance)/annuity),got=compute({G,P,r,n:m/12,mode:'date'});
  assert(got.ok);close(got.monthly,expected);assert(got.growth>=0);assert(got.contributed<=G);
  if(expected>0){const inverse=compute({G,P,r,c:expected,mode:'contrib'});assert(inverse.ok);close(inverse.months,m);}
});
// Accepted results must never leak nonfinite totals for any sampled finite input.
let seed=0x9213e;
const random=()=>((seed=(1664525*seed+1013904223)>>>0)/4294967296);
for(let k=0;k<2000;k++)test(`finite envelope ${k}`,()=>{
  const G=10**(-300+600*random()),P=G*random(),r=10**(-320+626*random());
  const mode=k%2?'date':'contrib',inp={G,P,r,mode,n:10**(-300+600*random()),c:10**(-300+600*random())};
  const out=compute(inp);if(!out.ok)return;
  for(const key of ['monthly','months','gap','contributed','growth'])assert(Number.isFinite(out[key]),key);
  assert(out.monthly>=0);assert(out.months>0);assert(out.gap>0);assert(out.growth>=0);assert(out.contributed>=P);assert(out.contributed<=G);
});
console.log(JSON.stringify({source:path,pass,fail}));
if(fail)process.exitCode=1;
