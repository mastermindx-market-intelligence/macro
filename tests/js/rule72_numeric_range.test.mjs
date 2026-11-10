/** Actual template/page controllers. Scripted DOM, not browser or OS clipboard proof. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import vm from 'node:vm';

const ROOT = process.env.RULE72_ROOT || resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const paths = ['templates/calculators/rule_of_72.html.j2', 'site/tools/calculators/rule-of-72.html'];
function script(path) {
  const s = readFileSync(resolve(ROOT,path),'utf8');
  const found = [...s.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(s=>s.includes('rule-of-72 self-check'));
  assert.equal(found.length,1); return found[0];
}
function compute(path, inp) {
  const source = script(path).replace('  // ── §6 self-check:', '  globalThis.compute = compute;\n  // ── §6 self-check:');
  const ctx = {document:{addEventListener(){}},console:{error(){assert.fail('worked example drift');}}};
  vm.runInNewContext(source,ctx); return ctx.compute(inp);
}
function page(path, language='en', legacy=false) {
  const nodes=new Map(), docEvents=new Map(), writes=[], errors=[];
  function node(id) {
    const events=new Map(),attrs=new Map(),classes=new Set();
    return {id,value:'',textContent:'',className:'',hidden:false,select(){},
      addEventListener:(t,f)=>events.set(t,f),fire:(t,e)=>events.get(t)(e),
      setAttribute:(k,v)=>attrs.set(k,v),getAttribute:k=>attrs.get(k),
      classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),toggle:(x,on)=>on?classes.add(x):classes.delete(x)}};
  }
  for(const id of ['row-rate','row-years','rate','years','out-main','out-unit','out-plain','out-est','out-exact','out-gap','copy-result','copied'])nodes.set(id,node(id));
  const seg=node('seg'),buttons=['rate','years'].map(v=>{const n=node(v);n.setAttribute('data-v',v);return n;});seg.querySelectorAll=()=>buttons;
  let selected=null;
  const document={documentElement:{getAttribute:k=>{assert.equal(k,'lang');return language;}},
    getElementById:id=>{assert.ok(nodes.has(id));return nodes.get(id);},querySelector:q=>{assert.equal(q,'.ci-seg[data-name="mode"]');return seg;},
    addEventListener:(t,f)=>docEvents.set(t,f),createElement:()=>node('textarea'),
    body:{appendChild:n=>{selected=n;},removeChild:()=>{selected=null;}},execCommand:()=>{writes.push(selected.value);return true;}};
  const navigator=legacy?{}:{clipboard:{writeText:t=>{writes.push(t);return Promise.resolve();}}};
  vm.runInNewContext(script(path),{document,navigator,console:{error:(...a)=>errors.push(a)},setTimeout(){}});
  docEvents.get('DOMContentLoaded')();assert.deepEqual(errors,[]);
  return {get:id=>nodes.get(id).textContent,writes,
    set(id,value){nodes.get(id).value=String(value);nodes.get(id).fire('input');},
    mode(value){const b=buttons.find(b=>b.getAttribute('data-v')===value);seg.fire('click',{target:{closest:()=>b}});},
    copy(){nodes.get('copy-result').fire('click');return writes.at(-1);}};
}
function close(a,b,rel=5e-15){assert.ok(Math.abs(a-b)<=Math.abs(b)*rel,`${a} != ${b}`);}
const outputs=['out-main','out-est','out-exact','out-gap'];
test('template and committed page have identical complete controllers',()=>assert.equal(script(paths[0]),script(paths[1])));
for(const path of paths){
  test(`${path} published fixtures retain stated rounding`,()=>{
    for(const [mode,x,est,exact] of [['rate',8,9,9.006468342000595],['rate',6,12,11.895661045941875],['years',10,7.2,7.177346253629316]]){
      const r=compute(path,{mode,r:x,y:x});assert.equal(r.ok,true);assert.equal(r.est,est);close(r.exact,exact);
    }
  });
  for(const [rate,expected] of [[1e-14,6931471805599453],[1e-12,69314718055994.88],[1e-10,693147180560.2919]]){
    test(`${path} positive tiny rate ${rate} retains finite exact years`,()=>{const r=compute(path,{r:rate});assert.equal(r.ok,true);close(r.exact,expected);});
  }
  test(`${path} very long horizon preserves positive required rate`,()=>{
    for(const y of [1e16,1e100,1e308]){const r=compute(path,{mode:'years',y});assert.equal(r.ok,true);assert.ok(r.exact>0);close(r.exact,100*Math.LN2/y,1e-14);}
  });
  for(const [mode,x] of [['rate',1e-307],['rate',5e-324],['years',0.0009],['years',5e-324]]){
    for(const lang of ['en','zh'])test(`${path} ${lang} ${mode}=${x} clears and refuses export then recovers`,()=>{
      const ui=page(path,lang);ui.set('rate',8);ui.copy();const n=ui.writes.length;
      ui.mode(mode);ui.set(mode==='rate'?'rate':'years',x);
      for(const id of outputs)assert.equal(ui.get(id),'—');
      assert.match(ui.get('out-plain'),lang==='en'?/numeric range/:/数值范围/);
      ui.copy();assert.equal(ui.writes.length,n);
      ui.mode('rate');ui.set('rate',8);assert.equal(ui.get('out-exact'),lang==='en'?'9.01 yr':'9.01 年');assert.match(ui.copy(),/exact 9\.01/);
    });
  }
  test(`${path} finite large results stay valid`,()=>{
    for(const inp of [{r:1e-306},{r:1e308},{mode:'years',y:0.001},{mode:'years',y:1e308}]){
      const r=compute(path,inp);assert.equal(r.ok,true);for(const k of ['est','exact','gap'])assert.ok(Number.isFinite(r[k]),k);assert.ok(r.exact>0);
    }
  });
  test(`${path} domain and nonfinite input controls refuse`,()=>{
    for(const x of [0,-1,NaN,Infinity,-Infinity])for(const mode of ['rate','years'])assert.equal(compute(path,{mode,r:x,y:x}).ok,false);
  });
  test(`${path} mode changes and repeated invalid input preserve refusal`,()=>{
    const ui=page(path);ui.set('rate',8);ui.set('years',0.0009);ui.mode('years');
    for(let i=0;i<3;i++){ui.copy();assert.equal(ui.writes.length,0);ui.set('years',0.0009);}
    ui.mode('rate');assert.equal(ui.get('out-exact'),'9.01 yr');ui.mode('years');assert.equal(ui.get('out-exact'),'—');
    ui.set('years',10);assert.equal(ui.get('out-exact'),'7.18%');assert.match(ui.copy(),/exact 7\.18%/);
  });
  test(`${path} tiny rate copy contains finite result; legacy refuses overflow`,()=>{
    const ui=page(path,'en',true);ui.set('rate',1e-14);assert.doesNotMatch(ui.copy(),/Infinity|NaN|∞/);
    const n=ui.writes.length;ui.set('rate',1e-307);ui.copy();assert.equal(ui.writes.length,n);
  });
  test(`${path} 300 ordinary inputs preserve formula within floating point tolerance`,()=>{
    for(let i=1;i<=300;i++){const r=i/10,y=i/7;
      close(compute(path,{r}).exact,Math.LN2/Math.log(1+r/100),3e-13);
      close(compute(path,{mode:'years',y}).exact,100*(2**(1/y)-1),3e-13);
    }
  });
}
