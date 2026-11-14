/** Executes the complete native Kelly controllers, not a reimplemented formula.
 * Contract: exact sign of canonical parsed decimal Numbers, no epsilon band.
 * Run: node --test tests/js/kelly_exact_zero.test.mjs
 * Set KELLY_ROOT to another source root for unchanged-source red tests.
 */
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { test as nodeTest } from 'node:test';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root=process.env.KELLY_ROOT || resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const paths=['templates/calculators/kelly_criterion.html.j2','site/tools/calculators/kelly-criterion.html'];
function controller(file){
 const scripts=[...fs.readFileSync(file,'utf8').matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
 const selected=scripts.filter(s=>s.includes('function compute(inp)')&&s.includes('winprob'));
 assert.equal(selected.length,1,'one complete Kelly controller'); return selected[0];
}
function load(file,bigint=BigInt){
 const nodes={},errors=[],writes=[];
 for(const id of ['winprob','wlratio','out-main','out-plain','out-half','out-edge','out-loss','copy-result','copied']) nodes[id]={value:'',textContent:'',className:'',listeners:{},addEventListener(k,f){this.listeners[k]=f;},classList:{add(){},remove(){}}};
 nodes.winprob.value='55';nodes.wlratio.value='2';let ready;
 const ctx={BigInt:bigint,console:{error(...v){errors.push(v)}},document:{addEventListener(k,f){ready=f;},getElementById(id){return nodes[id];}},navigator:{clipboard:{writeText(s){writes.push(s);return Promise.resolve();}}},setTimeout(){}};
 const source=controller(file).replace('  // ── DOM wiring','  globalThis.compute = compute;\n  // ── DOM wiring');
 vm.runInNewContext(source,ctx);ready();
 return {compute:ctx.compute,nodes,errors,writes,set(W,R){nodes.winprob.value=String(W);nodes.wlratio.value=String(R);nodes.winprob.listeners.input();},copy(){nodes['copy-result'].listeners.click();}};
}
nodeTest('template and committed-page controllers match',()=>assert.equal(controller(resolve(root,paths[0])),controller(resolve(root,paths[1]))));
for(const path of paths){
 const file=resolve(root,path);
 const test=(name,fn)=>nodeTest(path+': '+name,fn);
const x=load(file);
function neighbor(n,up){const a=new Float64Array([n]),b=new BigUint64Array(a.buffer);b[0]+=up?1n:-1n;return a[0];}
test('candidate self checks clean',()=>assert.equal(x.errors.length,0));
for(const [W,R] of [[40,1.5],[50,1],[20,4],[80,.25]])test('exact zero '+W+'/'+R,()=>{const v=x.compute({W,R});assert(v.ok&&v.noEdge);for(const key of ['f','kellyPct','halfKellyPct','edgeR'])assert(Object.is(v[key],0));});
test('ordinary 55/2',()=>{const v=x.compute({W:55,R:2});assert.equal(v.kellyPct,32.5);assert.equal(v.halfKellyPct,16.25);assert.equal(v.edgeR,.65);assert(!v.noEdge);});
for(const [W,R] of [[40,1.5],[50,1]])for(const axis of ['W','R'])for(const up of [false,true])test('nearest neighbor '+W+'/'+R+' '+axis+' '+up,()=>{const inp={W,R};inp[axis]=neighbor(inp[axis],up);const v=x.compute(inp);assert(v.ok);assert.equal(v.noEdge,!up);assert.equal(Math.sign(v.f),up?1:-1);assert.equal(Math.sign(v.edgeR),up?1:-1);});
for(const [W,R] of [[0,1],[100,1],[-1,1],[NaN,1],[50,0],[50,-1],[50,NaN],[50,Infinity],[Infinity,1]])test('invalid '+W+'/'+R,()=>assert.equal(x.compute({W,R}).ok,false));
test('overflow refuses; representable extreme remains valid',()=>{assert(!x.compute({W:50,R:Number.MIN_VALUE}).ok);assert(x.compute({W:Number.MIN_VALUE,R:Number.MAX_VALUE}).ok);});
test('BigInt unavailable gracefully refuses',()=>{const z=load(file,null);assert.equal(z.compute({W:40,R:1.5}).ok,false);assert(z.nodes['out-plain'].textContent.includes('BigInt'));z.copy();assert.equal(z.writes.length,0);});
test('zero DOM narrative style and copy',()=>{x.set(40,1.5);assert.equal(x.nodes['out-main'].textContent,'0%');assert.equal(x.nodes['out-half'].textContent,'0%');assert.equal(x.nodes['out-edge'].textContent,'0.00R');assert.equal(x.nodes['out-edge'].className,'neg');assert.equal(x.nodes['out-plain'].className,'co-plain warn');assert(x.nodes['out-plain'].textContent.startsWith('No positive edge'));x.copy();assert(x.writes.at(-1).includes("no positive edge — don't bet"));});
test('positive nearest neighbor DOM and copy remain positive',()=>{x.set(40,neighbor(1.5,true));assert(x.nodes['out-plain'].textContent.startsWith('Full Kelly stakes'));assert.equal(x.nodes['out-edge'].className,'pos');x.copy();assert(x.writes.at(-1).startsWith('Kelly criterion: 0.0% of capital'));});
test('negative nearest neighbor DOM and copy',()=>{x.set(40,neighbor(1.5,false));assert(x.nodes['out-plain'].textContent.startsWith('No positive edge'));assert.equal(x.nodes['out-edge'].className,'neg');x.copy();assert(x.writes.at(-1).includes('no positive edge'));});
test('range refusal clears output and copy; recovery works',()=>{x.set(50,Number.MIN_VALUE);for(const id of ['out-main','out-half','out-edge','out-loss'])assert.equal(x.nodes[id].textContent,'—');assert.equal(x.nodes['out-plain'].className,'co-plain');assert(x.nodes['out-plain'].textContent.includes('numeric range'));const n=x.writes.length;x.copy();assert.equal(x.writes.length,n);x.set(55,2);assert.equal(x.nodes['out-main'].textContent,'32.5%');assert.equal(x.nodes['out-edge'].className,'pos');x.copy();assert.equal(x.writes.length,n+1);});
test('existing parseFloat prefix behavior retained',()=>{x.set('40junk','1.5junk');assert.equal(x.nodes['out-main'].textContent,'0%');});

}
