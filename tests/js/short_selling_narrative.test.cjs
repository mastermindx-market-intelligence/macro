'use strict';
const fs=require('node:fs'); const path=require('node:path');const vm=require('node:vm');const assert=require('node:assert/strict');const test=require('node:test');
const dir=process.env.CALC_ROOT||path.resolve(__dirname,'../..');
const filenames=['templates/calculators/short_selling.html.j2','site/tools/calculators/short-selling.html'];
const numericIds=['out-main','out-gross','out-borrow','out-ret'];
function load(filename){
 const source=fs.readFileSync(filename,'utf8');const scripts=[...source.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(x=>x[1]);const script=scripts.find(x=>x.includes('short-selling self-check'));assert.ok(script);
 const nodes={};for(const id of ['entry','cover','shares','bfee','days',...numericIds,'out-plain','copy-result','copied'])nodes[id]={value:'',textContent:'',className:'',events:{},addEventListener(k,f){this.events[k]=f},classList:{add(){},remove(){}}};
 const copied=[],errors=[];let ready;const context={document:{getElementById:id=>nodes[id],addEventListener:(k,f)=>{assert.equal(k,'DOMContentLoaded');ready=f}},navigator:{clipboard:{writeText(s){copied.push(s);return Promise.resolve()}}},console:{error:(...x)=>errors.push(x)},setTimeout(){}};
 vm.runInNewContext(script,context,{filename});ready();assert.deepEqual(errors,[],'canonical self-checks');
 return {nodes,copied,set(values){for(const k of ['entry','cover','shares','bfee','days'])nodes[k].value=String(values[k]??'');nodes.entry.events.input();return this.snapshot()},snapshot(){return Object.fromEntries([...numericIds,'out-plain'].map(k=>[k,nodes[k].textContent]))},copy(){nodes['copy-result'].events.click();return copied.at(-1)}};
}
const common={entry:50,cover:49,shares:100,bfee:5,days:365};
const cases=[
 ['favorable price move, fee-driven loss',common,'-$150.00',/borrow costs outweighed the profit from the price decline/],
 ['unchanged price, fee-only loss',{...common,cover:50},'-$250.00',/price was unchanged and borrow costs caused the loss/],
 ['adverse price move without borrow',{...common,cover:51,bfee:'',days:''},'-$100.00',/stock rose against the position/],
 ['adverse price move with borrow',{...common,cover:51},'-$350.00',/stock rose against the position/],
 ['normal gain after borrow',{...common,cover:40,days:30},'$979.45',/This short made/],
 ['no-borrow gain',{...common,bfee:'',days:''},'$100.00',/This short made/],
 ['no-borrow flat',{...common,cover:50,bfee:'',days:''},'$0.00',/broke even/],
 ['borrow exactly offsets gain',{...common,cover:47.5},'$0.00',/broke even/],
 ['one optional missing retains explicit existing contract',{...common,days:''},'$100.00',/This short made/],
 ['small fee-driven loss',{entry:50,cover:49.99,shares:100,bfee:5,days:30},'-$19.55',/borrow costs outweighed/],
 ['invalid required input',{...common,entry:''},'—',/Enter the price/]
];
for(const filename of filenames){
 for(const [name,values,net,why] of cases)test(filename+': '+name,()=>{const x=load(path.join(dir,filename));const got=x.set(values);assert.equal(got['out-main'],net);assert.match(got['out-plain'],why);if(net.startsWith('-$')){assert.match(got['out-plain'],new RegExp('This short lost \\$'));assert.doesNotMatch(got['out-plain'],/lost -\$/)} });
 test(filename+': loss causes update on repeated input events',()=>{const x=load(path.join(dir,filename));x.set(common);assert.match(x.snapshot()['out-plain'],/borrow costs outweighed/);x.set({...common,cover:51});assert.match(x.snapshot()['out-plain'],/stock rose/);x.set({...common,cover:50});assert.match(x.snapshot()['out-plain'],/price was unchanged/);x.set({...common,cover:40});assert.doesNotMatch(x.snapshot()['out-plain'],/stock rose|costs outweighed|price was unchanged/);assert.equal(x.nodes['out-plain'].className,'co-plain');x.set(common);assert.equal(x.nodes['out-plain'].className,'co-plain warn');});
 test(filename+': financial outputs and copy retain canonical fee-loss values',()=>{const x=load(path.join(dir,filename));const a=x.set(common);assert.deepEqual(numericIds.map(id=>a[id]),['-$150.00','$100.00','$250.00','-3.00%']);assert.equal(x.copy(),'Short selling loss: -$150.00 (-3.00% on notional) · gross $100.00 · borrow $250.00 — mastermind-x.com');x.set({...common,cover:40,days:30});assert.equal(x.copy(),'Short selling profit: $979.45 (19.6% on notional) · gross $1,000.00 · borrow $20.55 — mastermind-x.com');});
 test(filename+': invalid state clears old computed result and prevents copy',()=>{const x=load(path.join(dir,filename));x.set(common);x.set({...common,entry:''});assert.equal(x.copy(),undefined);for(const id of numericIds)assert.equal(x.nodes[id].textContent,'—')});
}
test('template and generated calculator controllers remain byte-identical',()=>{function pick(f){return [...fs.readFileSync(f,'utf8').matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(x=>x[1]).find(x=>x.includes('short-selling self-check'))}assert.equal(pick(path.join(dir,filenames[0])),pick(path.join(dir,filenames[1])))});
