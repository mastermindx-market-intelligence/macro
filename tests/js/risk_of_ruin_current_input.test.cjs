const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync(process.argv[2],'utf8');
const script=[...source.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x=>x[1]).find(x=>x.includes('function simulate(p)'));
assert.ok(script,'full calculator inline script');
function harness({worker=true,lang="en",clipboard,legacy=false,execResult=true}={}){
 const nodes={},timers=new Map(),writes=[],workers=[],errors=[];let tick=0,id=0,blobScript;
 function node(id){return nodes[id]??={id,value:'',textContent:'',className:'',style:{},handlers:{},classList:{s:new Set(),add(x){this.s.add(x)},remove(x){this.s.delete(x)},contains(x){return this.s.has(x)}},addEventListener(k,f){this.handlers[k]=f}}}
 for(const id of ['winrate','payoff','riskpct','ruindd','trades'])node(id);
 Object.assign(nodes.winrate,{value:'50'});nodes.payoff.value='1';nodes.riskpct.value='2';nodes.ruindd.value='50';nodes.trades.value='500';
 const document={documentElement:{getAttribute(){return lang}},getElementById:node,addEventListener(k,f){if(k==='DOMContentLoaded')f()}};
 document.body={children:[],appendChild(n){this.children.push(n)},removeChild(n){this.children.splice(this.children.indexOf(n),1)}};
 document.createElement=()=>({value:'',select(){}});
 document.execCommand=()=>{if(execResult instanceof Error)throw execResult;return execResult};
 const setTimeout=(f,ms)=>{timers.set(++id,{f,at:tick+ms});return id},clearTimeout=id=>timers.delete(id);
 class Blob{constructor(parts){this.source=parts.join('')}}
 class Worker{constructor(){this.requests=[];this.dead=false;workers.push(this);this.workerContext={Math,self:{postMessage:d=>this.onmessage({data:d})}};vm.runInNewContext(blobScript,this.workerContext)}postMessage(d){this.requests.push(d)}terminate(){this.dead=true}deliver(index){this.workerContext.self.onmessage({data:this.requests[index]})}}
 const window={Blob,Worker:worker?Worker:undefined,URL:{createObjectURL(b){blobScript=b.source;return 'blob:fixture'}},requestIdleCallback(){}};
 vm.runInNewContext(script,{document,window,Blob,Worker,navigator:{clipboard:legacy?undefined:{writeText(s){writes.push(s);return clipboard?clipboard():Promise.resolve()}}},console:{error(...a){errors.push(a)}},setTimeout,clearTimeout});
 return {nodes,workers,writes,errors,document,input(k,v){node(k).value=v;node(k).handlers.input()},copy(){node('copy-result').handlers.click()},advance(ms){const target=tick+ms;for(;;){const ready=[...timers].filter(([i,t])=>t.at<=target).sort((a,b)=>a[1].at-b[1].at);if(!ready.length)break;const [i,t]=ready[0];timers.delete(i);tick=t.at;t.f()}tick=target},result(){return node('out-main').textContent},plain(){return node('out-plain').textContent}};
}
let pass=0,fail=0;function test(name,f){try{f();pass++;console.log('PASS '+name)}catch(e){fail++;console.log('FAIL '+name+': '+e.message)}}
test('baseline initial worker result matches deterministic fixed-seed core',()=>{const h=harness();h.workers[0].deliver(0);assert.equal(h.result(),'16.1%');h.copy();assert.match(h.writes[0],/16.1%.*500 trades/)});
test('edit invalidates in-flight response before debounce',()=>{const h=harness();h.input('winrate','100');h.workers[0].deliver(0);assert.equal(h.result(),'—');assert.ok(!h.plain().includes('16.1%'));h.copy();assert.equal(h.writes.length,0)});
test('edit clears completed old result and copy immediately',()=>{const h=harness();h.workers[0].deliver(0);h.input('winrate','100');assert.equal(h.result(),'—');h.copy();assert.equal(h.writes.length,0)});
test('current frame never combines new expectancy with prior ruin',()=>{const h=harness();h.workers[0].deliver(0);h.input('winrate','100');h.advance(150);assert.equal(h.nodes['out-exp'].textContent,'+1.00 R');assert.equal(h.result(),'—');h.copy();assert.equal(h.writes.length,0);h.workers[0].deliver(1);assert.equal(h.result(),'0.00%');h.copy();assert.match(h.writes[0],/0.00%.*\+1.00 R/)});
test('blank invalid input invalidates immediately',()=>{const h=harness();h.input('riskpct','');h.workers[0].deliver(0);assert.equal(h.result(),'—');h.copy();assert.equal(h.writes.length,0);h.advance(150);assert.match(h.plain(),/percent of equity/)});
test('rapid edits dispatch only settled intent',()=>{const h=harness();h.input('winrate','100');h.advance(100);h.input('winrate','0');h.advance(149);assert.equal(h.workers[0].requests.length,1);h.advance(1);assert.equal(h.workers[0].requests.length,2);h.workers[0].deliver(1);assert.equal(h.result(),'100.0%');h.workers[0].deliver(0);assert.equal(h.result(),'100.0%')});
test('worker failure preserves latest inputs with deterministic sync fallback',()=>{const h=harness();h.input('winrate','100');h.workers[0].onerror();assert.equal(h.result(),'0.00%');assert.equal(h.workers[0].dead,true);h.workers[0].deliver(0);assert.equal(h.result(),'0.00%')});
test('no-worker path preserves deterministic compute and edit debounce',()=>{const h=harness({worker:false});assert.equal(h.result(),'16.1%');h.input('winrate','0');h.advance(150);assert.equal(h.result(),'100.0%');assert.equal(h.workers.length,0)});
test('empty optional fields retain defaults and cap remains',()=>{const h=harness({worker:false});h.input('ruindd','');h.input('trades','');h.advance(150);assert.equal(h.nodes['out-dd'].textContent,'50%');assert.equal(h.nodes['out-n'].textContent,'500');h.input('trades','100000');h.advance(150);assert.equal(h.nodes['out-n'].textContent,'1,000');assert.match(h.plain(),/capped at 1,000/)});
for(const [field,value] of [['winrate','100'],['payoff','2'],['riskpct','1'],['ruindd','25'],['trades','100']])test('every editable assumption invalidates result: '+field,()=>{const h=harness();h.workers[0].deliver(0);h.input(field,value);assert.equal(h.result(),'—');assert.equal(h.nodes['out-exp'].textContent,'—');assert.equal(h.nodes['copy-result'].disabled,true);h.copy();assert.equal(h.writes.length,0);h.advance(150);h.workers[0].deliver(1);assert.equal(h.nodes['copy-result'].disabled,false);assert.notEqual(h.result(),'—')});
test('A to B to A still fences the first A before new A completes',()=>{const h=harness();h.input('winrate','100');h.advance(50);h.input('winrate','50');h.workers[0].deliver(0);assert.equal(h.result(),'—');h.advance(150);h.workers[0].deliver(1);assert.equal(h.result(),'16.1%')});
test('same-value input event can safely recalculate and restore copy',()=>{const h=harness();h.workers[0].deliver(0);h.input('winrate','50');assert.equal(h.nodes['copy-result'].disabled,true);h.advance(150);h.workers[0].deliver(1);assert.equal(h.result(),'16.1%');assert.equal(h.nodes['copy-result'].disabled,false)});
test('newest result restores programmatic copy after blocked pending click',()=>{const h=harness();h.workers[0].deliver(0);h.input('winrate','100');h.copy();h.advance(150);h.copy();assert.equal(h.writes.length,0);h.workers[0].deliver(1);h.copy();assert.match(h.writes[0],/0.00%/)});
for(const lang of ['en','zh'])test('honest pending label '+lang,()=>{const h=harness({lang});h.input('winrate','100');assert.match(h.plain(),lang==='zh'?/正在按当前输入重新计算/:/Recalculating for the current inputs/)});
(async()=>{for(const settle of ['resolve','reject']){let resolve,reject;const h=harness({clipboard:()=>new Promise((a,b)=>{resolve=a;reject=b})});h.workers[0].deliver(0);h.copy();h.input('winrate','100');settle==='resolve'?resolve():reject(Error('denied'));await new Promise(r=>setImmediate(r));test('late clipboard '+settle+' cannot acknowledge old inputs',()=>assert.equal(h.nodes.copied.classList.contains('show'),false))}

async function copyTest(name, fn){
  try { await fn(); pass++; console.log('PASS '+name); }
  catch(e){fail++; console.log('FAIL '+name+': '+e.message);}
}
const settle=()=>new Promise(r=>setImmediate(r));
function ready(options){const h=harness(options);h.workers[0].deliver(0);return h;}
function shown(h){return h.nodes.copied.classList.contains('show');}
for(const lang of ['en','zh']){
  await copyTest('successful Clipboard acknowledgement '+lang,async()=>{
    const h=ready({lang});h.copy();await settle();assert.equal(shown(h),true);
    assert.match(h.writes[0],/^Risk of ruin: 16\.1%/);h.advance(1600);assert.equal(shown(h),false);
  });
  await copyTest('rejected Clipboard never acknowledges '+lang,async()=>{
    const h=ready({lang,clipboard:()=>Promise.reject(Error('denied'))});
    h.copy();await settle();assert.equal(shown(h),false);
  });
}
await copyTest('synchronous Clipboard failure is contained',async()=>{
  const h=ready({clipboard:()=>{throw Error('denied')}});h.copy();await settle();assert.equal(shown(h),false);
});
for(const result of [true,false,new Error('denied')]){
  await copyTest('legacy return '+String(result),async()=>{
    const h=ready({legacy:true,execResult:result});h.copy();
    assert.equal(shown(h),result===true);assert.equal(h.document.body.children.length,0);
    assert.equal(h.result(),'16.1%');
  });
}
await copyTest('failed copy clears prior success immediately',async()=>{
  let n=0;const h=ready({clipboard:()=>++n===1?Promise.resolve():Promise.reject(Error('denied'))});
  h.copy();await settle();assert.equal(shown(h),true);h.copy();assert.equal(shown(h),false);
  await settle();assert.equal(shown(h),false);
});
await copyTest('older success cannot affirm latest failed copy',async()=>{
  const p=[];const h=ready({clipboard:()=>new Promise((resolve,reject)=>p.push({resolve,reject}))});
  h.copy();h.copy();p[1].reject(Error('denied'));await settle();p[0].resolve();await settle();
  assert.equal(shown(h),false);
});
await copyTest('older failure cannot erase latest success',async()=>{
  const p=[];const h=ready({clipboard:()=>new Promise((resolve,reject)=>p.push({resolve,reject}))});
  h.copy();h.copy();p[1].resolve();await settle();p[0].reject(Error('denied'));await settle();
  assert.equal(shown(h),true);
});
await copyTest('old success timer cannot clear a newer success',async()=>{
  const h=ready();h.copy();await settle();h.advance(800);h.copy();await settle();
  h.advance(800);assert.equal(shown(h),true);h.advance(800);assert.equal(shown(h),false);
});
console.log(JSON.stringify({source:process.argv[2],pass,fail}));process.exitCode=fail?1:0;})();
