const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[2]||'site/odds.js','utf8');
function harness(){
 const downloads=[],images=[],pending=[],timers=[];
 const ctx=new Proxy({measureText:s=>({width:String(s).length*5})},{get:(o,k)=>o[k]||(()=>{})});
 const doc={documentElement:{getAttribute:()=>null},querySelector:()=>null,querySelectorAll:()=>[],body:{appendChild:()=>{}},createElement(tag){return tag==='canvas'?{getContext:()=>ctx,toDataURL:()=> 'data:image/png;base64,x'}:{click(){downloads.push(this.download)},remove(){}}}};
 const env={document:doc,window:{},URL,URLSearchParams,location:{search:''},Blob,console,getComputedStyle:()=>({getPropertyValue:()=>''}),fetch:()=>new Promise(resolve=>pending.push(resolve)),setTimeout:(f,ms)=>{timers.push({f,ms});return timers.length},clearTimeout(){},Image:function(){images.push(this)}};
 env.URL={createObjectURL:()=> 'blob:x',revokeObjectURL(){}};
 let instrumented=source.replace('  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);\n  else init();',`  renderSkeletons=function(){}; updateTopChrome=function(){}; renderRail=function(){}; recompute=function(){};
 globalThis.test={S:S,loadTicker:loadTicker,downloadCSV:downloadCSV,buildShareCard:buildShareCard};`);
 assert.notEqual(instrumented,source);vm.runInNewContext(instrumented,env);
 const api=env.test;Object.assign(api.S,{ticker:'AAA',horizon:'1d',range:'max',matrix:{schema:'odds_matrix.v1',dates:[19000,19001],close:[100,101],cols:{fwd1_bp:[100,null]},asof:'2022-01-09'},matches:[0],stats:{n:10,rate:.7,med:100,mean:100},base:{rate:.5},cat:{universe:[{t:'AAA',name:'First'}]}});
 // Use the source's configured horizon/range keys.
 api.S.horizon='1d';api.S.range='max';
 return {...api,downloads,images,pending,timers};
}
const cases={
 'pending ticker clears prior evidence':async()=>{let h=harness();h.loadTicker('BBB');assert.equal(h.S.matrix,null);assert.equal(h.S.stats,null);assert.equal(h.S.base,null);assert.equal(h.S.matches.length,0);h.downloadCSV();assert.equal(h.downloads.length,0)},
 'latest response wins':async()=>{let h=harness(),m=h.S.matrix;h.loadTicker('BBB');h.loadTicker('CCC');h.pending[1]({ok:true,json:async()=>({...m,close:[300,301]})});await new Promise(setImmediate);h.pending[0]({ok:true,json:async()=>m});await new Promise(setImmediate);assert.equal(h.S.ticker,'CCC');assert.equal(h.S.matrix.close[0],300)},
 'failed response stays unavailable':async()=>{let h=harness();h.loadTicker('BBB');h.pending[0]({ok:false});await new Promise(setImmediate);assert.equal(h.S.matrix,null);h.downloadCSV();assert.equal(h.downloads.length,0)},
 'share cancelled after ticker change':async()=>{let h=harness();h.buildShareCard({});assert.equal(h.images.length,1);h.S.ticker='BBB';h.images[0].onerror();assert.equal(h.downloads.length,0)},
 'share cancelled after horizon change':async()=>{let h=harness();h.buildShareCard({});h.S.horizon='5d';h.images[0].onerror();assert.equal(h.downloads.length,0)},
 'share cancelled after stats change':async()=>{let h=harness();h.buildShareCard({});h.S.stats={...h.S.stats,rate:.2};h.images[0].onerror();assert.equal(h.downloads.length,0)},
 'unchanged share downloads once':async()=>{let h=harness();h.buildShareCard({});h.images[0].onerror();assert.equal(h.downloads.length,1);h.images[0].onload();h.timers.find(x=>x.ms===1500).f();assert.equal(h.downloads.length,1);assert.match(h.downloads[0],/^odds_AAA_1d_/)},
 'unchanged CSV exports original ticker':async()=>{let h=harness();h.downloadCSV();assert.equal(h.downloads.length,1);assert.match(h.downloads[0],/^odds_AAA_1d_/)}
};
(async()=>{let fail=0;for(let [name,test] of Object.entries(cases)){if(process.argv[3]&&process.argv[3]!==name)continue;try{await test();console.log('PASS '+name)}catch(e){fail++;console.log('FAIL '+name+': '+e.message)}}process.exitCode=fail?1:0})();
