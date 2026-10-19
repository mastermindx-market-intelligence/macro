'use strict';
const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const sourceFile=()=>process.env.LIVE_REFRESH_SOURCE||path.join(__dirname,'../templates/heatmap.js');
const clone=v=>JSON.parse(JSON.stringify(v));
const flush=async()=>{for(let i=0;i<5;i++)await new Promise(r=>setImmediate(r));};
function base(overrides={}){
 return {market:'china',map_type:'stocks',source:'daily-close',asof:'2026-09-24',generated_utc:'2026-09-28 00:15',n_tiles:2,default_tf:'1D',
  timeframes:[{key:'1D',available:true},{key:'1W',available:true}],sectors:[{key:'Consumer',en:'Consumer',zh:'消费'}],
  tiles:[{t:'600519.SS',sector:'Consumer',size:100,perf:{'1D':1,'1W':3}},{t:'000001.SZ',sector:'Financial',size:50,perf:{'1D':-1,'1W':2}}],...clone(overrides)};
}
const NOW=Date.parse('2026-09-28T02:15:40Z');
function live(overrides={}){
 const ts=Date.parse('2026-09-28T02:15:30Z');
 const quotes={
  '600519.SS':{price:1412.8,prevClose:1398,changePct:(1412.8/1398-1)*100,ts,open:1399.5,high:1418,low:1390.1,vol:10,amount:100},
  '000001.SZ':{price:11.1,prevClose:11.2,changePct:(11.1/11.2-1)*100,ts:ts-1000,open:11.2,high:11.25,low:11,vol:20,amount:200},
 };
 return {schema:'china_heatmap_live.v1',market:'china',map_type:'stocks',baseline_asof:'2026-09-24',session_date:'2026-09-28',phase:'morning',status:'live',source:'tushare-rt-k',generated_at:'2026-09-28T02:15:40+00:00',source_observed_at:'2026-09-28T02:15:30+00:00',requested:2,resolved:2,coverage:1,usable:true,fallback:false,quotes,breadth:{n:2,adv:1,dec:1,flat:0,pctUp:50},...clone(overrides)};
}
function harness(queue=[]){
 let now=NOW,id=0;const timers=new Map(),intervals=[],events=[],calls=[];
 class FakeDate extends Date{static now(){return now;}}
 const context={Promise,URL,Date:FakeDate,Number,JSON,Object,Array,Math,Error,TypeError,Set,AbortController,
  setInterval:fn=>{intervals.push(fn);return intervals.length;},clearInterval:()=>{},
  setTimeout:(fn,delay)=>{timers.set(++id,{fn,delay});return id;},clearTimeout:n=>timers.delete(n),
  fetch:async(url,opts)=>{calls.push({url,opts});if(!queue.length)throw new Error('No response queued');const x=queue.shift();if(x instanceof Error)throw x;if(typeof x==='function')return x(opts);return {ok:true,status:200,json:async()=>clone(x)};},
  document:{hidden:false,dispatchEvent:e=>events.push(e)},CustomEvent:function(type,opts){this.type=type;this.detail=opts.detail;},console};
 vm.createContext(context);let raw=fs.readFileSync(sourceFile(),'utf8');const start=raw.indexOf('  var JSON_URL =');const end=raw.indexOf('  /* ---- per-timeframe colour-scale floors',start);if(start<0||end<0)throw new Error('loader boundary missing');raw=raw.slice(start,end);
 vm.runInContext(raw+'\nglobalThis.api={validateChinaLiveSnapshot,commitChinaLiveSnapshot,startChinaLiveRefresh,chinaLiveValue,chinaLiveMeta,_chinaLiveStates};',context,{filename:sourceFile()});
 const runTimer=async (predicate)=>{let found;for(const [key,t] of timers){if(!predicate||predicate(t)){found=[key,t];break;}}if(!found)throw new Error('No matching timer');timers.delete(found[0]);found[1].fn();await flush();return found[1].delay;};
 return {context,queue,timers,events,calls,base,live,clone,setNow:v=>{now=v;},validate:(p,b)=>context.api.validateChinaLiveSnapshot(p,b,now),commit:(url,p)=>context.api.commitChinaLiveSnapshot(url,p),start:b=>context.api.startChinaLiveRefresh(b),value:(b,t,tf)=>context.api.chinaLiveValue(b,t,tf),meta:b=>context.api.chinaLiveMeta(b),runTimer,flush};
}
module.exports={harness,base,live,clone,flush,NOW};
