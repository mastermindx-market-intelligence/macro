/** Real inline controller execution. Scripted DOM/clipboard, not browser proof.
 * node --test tests/js/stop_price_precision.test.mjs
 */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
import test from 'node:test';
const ROOT=process.env.STOP_TEST_ROOT || join(dirname(fileURLToPath(import.meta.url)),'..','..');
const paths=['templates/calculators/stop_loss_take_profit.html.j2','site/tools/calculators/stop-loss-take-profit.html'];
function scriptAt(path){
  const scripts=[...readFileSync(join(ROOT,path),'utf8').matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(s=>s.includes('function compute(inp)'));
  assert.equal(scripts.length,1);return scripts[0];
}
const scripts=paths.map(scriptAt);
test('template and committed page controllers are identical',()=>assert.equal(...scripts));
function page(script,{legacy=false}={}){
 const nodes=new Map(),events=new Map(),writes=[],errors=[];let textarea;
 function node(id){const handlers=new Map(),attrs=new Map(),classes=new Set();return {id,value:'',textContent:'',className:'',classList:{add:n=>classes.add(n),remove:n=>classes.delete(n),contains:n=>classes.has(n),toggle(n,v){v?classes.add(n):classes.delete(n);}},addEventListener:(n,f)=>handlers.set(n,f),fire(n,e={}){assert.ok(handlers.has(n),'listener '+n);handlers.get(n)(e);},getAttribute:n=>attrs.get(n)||null,setAttribute:(n,v)=>attrs.set(n,String(v)),querySelectorAll:()=>[],select(){}};}
 for(const id of ['entry','stoppct','targetpct','shares','out-main','out-unit','out-plain','out-stop','out-target','out-rr','out-drisk','out-dreward','copy-result','copied'])nodes.set(id,node(id));
 const html=node('html'),seg=node('seg');html.setAttribute('data-lang','en');
 const document={documentElement:html,getElementById:id=>{assert.ok(nodes.has(id),id);return nodes.get(id);},querySelector:s=>{assert.equal(s,'.ci-seg[data-name="side"]');return seg;},addEventListener:(n,f)=>events.set(n,f),createElement:()=>node('textarea'),body:{appendChild:n=>{textarea=n;},removeChild(){}},execCommand:()=>{writes.push(textarea.value);return true;}};
 const navigator=legacy?{}:{clipboard:{writeText:s=>{writes.push(s);return Promise.resolve();}}};
 const ctx=vm.createContext({document,navigator,console:{error:(...x)=>errors.push(x)},setTimeout(){}});
 vm.runInContext(script,ctx);assert.ok(events.has('DOMContentLoaded'));events.get('DOMContentLoaded')();assert.deepEqual(errors,[],'embedded worked examples');
 return {get:id=>nodes.get(id).textContent,writes,fill(values){for(const [id,v] of Object.entries(values))nodes.get(id).value=String(v);nodes.get('entry').fire('input');},side(value){const b=node('side');b.setAttribute('data-v',value);seg.fire('click',{target:{closest:()=>b}});},copy(){nodes.get('copy-result').fire('click');},language(value){html.setAttribute('data-lang',value);if(events.has('langchange'))events.get('langchange')();},values(){return Object.fromEntries(['entry','stoppct','targetpct','shares'].map(id=>[id,nodes.get(id).value]));}};
}
const base={entry:1,stoppct:.1,targetpct:.3,shares:100000};
const amount=s=>Number(s.replaceAll(',','').replace('$',''));
for(const [index,script] of scripts.entries()){
 const label=paths[index];
 for(const [side,stop,target] of [['long','$0.999','$1.003'],['short','$1.001','$0.997']]){
  test(`${label}: ${side} sub-cent levels survive cards, narrative and modern copy`,()=>{
   const p=page(script);p.fill(base);p.side(side);assert.equal(p.get('out-stop'),stop);assert.equal(p.get('out-target'),target);assert.equal(p.get('out-main'),target);assert.ok(p.get('out-plain').includes('at $1.00'));assert.ok(p.get('out-plain').includes('stop at '+stop));assert.ok(p.get('out-plain').includes('target at '+target));assert.equal(p.get('out-rr'),'3 : 1');assert.equal(p.get('out-drisk'),'$100.00');assert.equal(p.get('out-dreward'),'$300.00');p.copy();assert.ok(p.writes[0].includes('stop '+stop+' · target '+target));
  });
  test(`${label}: ${side} sub-cent legacy copy retains the same levels`,()=>{const p=page(script,{legacy:true});p.fill(base);p.side(side);p.copy();assert.ok(p.writes[0].includes('stop '+stop+' · target '+target));});
 }
 test(`${label}: ordinary cents and worked examples keep familiar amounts`,()=>{
  const p=page(script);p.fill({entry:10,stoppct:.1,targetpct:.3,shares:100000});assert.equal(p.get('out-stop'),'$9.99');assert.equal(p.get('out-target'),'$10.03');
  p.fill({entry:100,stoppct:5,targetpct:15,shares:100});assert.equal(p.get('out-stop'),'$95.00');assert.equal(p.get('out-target'),'$115.00');assert.equal(p.get('out-drisk'),'$500.00');assert.equal(p.get('out-dreward'),'$1,500.00');p.side('short');assert.equal(p.get('out-stop'),'$105.00');assert.equal(p.get('out-target'),'$85.00');
 });
 test(`${label}: near-adjacent native levels are never merged by 15-digit formatting`,()=>{
  const p=page(script);p.fill({entry:1,stoppct:1e-14,targetpct:3e-14,shares:''});assert.equal(amount(p.get('out-stop')),1*(1-1e-16));assert.equal(amount(p.get('out-target')),1*(1+3e-16));assert.ok(amount(p.get('out-stop'))<1);assert.ok(amount(p.get('out-target'))>1);p.copy();assert.ok(p.writes[0].includes(p.get('out-stop')));assert.ok(p.writes[0].includes(p.get('out-target')));
 });
 test(`${label}: scientific notation preserves tiny finite positive prices`,()=>{const p=page(script);p.fill({entry:1e-100,stoppct:10,targetpct:20,shares:''});assert.equal(p.get('out-stop'),'$9e-101');assert.equal(p.get('out-target'),'$1.2e-100');p.copy();assert.ok(p.writes[0].includes('$9e-101'));});
 test(`${label}: finite levels near maximum do not become infinity through formatting`,()=>{const p=page(script);p.fill({entry:1e308,stoppct:10,targetpct:79.76931348623155,shares:''});assert.equal(amount(p.get('out-target')),1e308*(1+79.76931348623155/100));p.side('short');
  p.fill({entry:1e308,stoppct:1,targetpct:1,shares:''});assert.ok(Number.isFinite(amount(p.get('out-stop'))));assert.ok(Number.isFinite(amount(p.get('out-target'))));assert.equal(amount(p.get('out-stop')),1.01e308);assert.equal(amount(p.get('out-target')),9.9e307);
 });
 test(`${label}: commas in input and grouped prices remain readable`,()=>{const p=page(script);p.fill({entry:'1,234.56789',stoppct:10,targetpct:20,shares:''});assert.equal(p.get('out-stop'),'$1,111.111101');assert.equal(p.get('out-target'),'$1,481.481468');assert.ok(p.get('out-plain').includes('$1,234.56789'));});
 test(`${label}: model/tick/fill caveat travels with screen and copy in EN/ZH`,()=>{
  const p=page(script);p.fill(base);assert.match(p.get('out-plain'),/Approximate model prices, not tick-rounded; fills are not guaranteed/);p.copy();assert.match(p.writes.at(-1),/Approximate model prices/);const before=p.values();p.language('zh');assert.deepEqual(p.values(),before);assert.match(p.get('out-plain'),/价格为近似模型值/);p.copy();assert.match(p.writes.at(-1),/未按交易最小变动单位取整；不保证成交/);p.language('en');assert.match(p.get('out-plain'),/Approximate model prices/);
 });
 test(`${label}: invalid, below-zero and recovery paths clear and restore current values`,()=>{
  const p=page(script);p.fill(base);p.copy();assert.equal(p.writes.length,1);for(const changes of [{entry:''},{stoppct:''},{stoppct:-1},{stoppct:100},{targetpct:''}]){p.fill({...base,...changes});for(const id of ['out-main','out-stop','out-target','out-rr','out-drisk','out-dreward'])assert.equal(p.get(id),'—');p.copy();assert.equal(p.writes.length,1);}
  p.fill(base);p.side('short');p.fill({...base,targetpct:100});assert.equal(p.get('out-main'),'—');p.copy();assert.equal(p.writes.length,1);p.fill(base);p.copy();assert.equal(p.writes.length,2);assert.ok(p.writes.at(-1).includes('stop $1.001 · target $0.997'));
 });
 test(`${label}: optional shares preserve levels but withhold dollar amounts`,()=>{const p=page(script);p.fill({...base,shares:''});assert.equal(p.get('out-stop'),'$0.999');assert.equal(p.get('out-drisk'),'—');assert.equal(p.get('out-dreward'),'—');p.copy();assert.ok(!p.writes.at(-1).includes(' · risk $'));});
 test(`${label}: 840 finite fixture prices preserve direction and stated precision`,()=>{
  const p=page(script);let count=0;
  for(const E of [1e-100,1e-8,.000123,1,12.3456789,1e6,1e100])for(const sp of [1e-14,1e-10,.0001,.1,10,50])for(const tp of [3e-14,1e-8,.0003,.3,20])for(const side of ['long','short']){
   p.fill({entry:E,stoppct:sp,targetpct:tp,shares:''});p.side(side);const stop=E*(1+(side==='long'?-1:1)*sp/100),target=E*(1+(side==='long'?1:-1)*tp/100);const gotStop=amount(p.get('out-stop')),gotTarget=amount(p.get('out-target'));
   for(const [want,got] of [[stop,gotStop],[target,gotTarget]])assert.ok(Math.abs(got-want)/Math.abs(want)<6e-15,`${side} ${E} ${want} ${got}`);
   if(stop!==target)assert.notEqual(gotStop,gotTarget);if(stop!==E)assert.equal(Math.sign(gotStop-E),Math.sign(stop-E));if(target!==E)assert.equal(Math.sign(gotTarget-E),Math.sign(target-E));count++;
  }assert.equal(count,420);
 });
}
