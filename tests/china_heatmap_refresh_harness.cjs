'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const sourceFile = () => process.env.REFRESH_SOURCE || path.join(__dirname,'../templates/heatmap.js');
const clone = value => JSON.parse(JSON.stringify(value));
const flush = async () => { for (let i=0;i<4;i++) await new Promise(resolve=>setImmediate(resolve)); };
function payload(overrides={}) {
 return {market:'china',map_type:'stocks',source:'daily-close',asof:'2026-09-18',
  generated_utc:'2026-09-18 15:40',n_tiles:2,default_tf:'1D',
  timeframes:[{key:'1D',available:true},{key:'1W',available:true}],
  sectors:[{key:'Technology',en:'Technology',zh:'信息技术'}],
  tiles:[{t:'A',name:'Alpha',sector:'Technology',size:100,perf:{'1D':1,'1W':3}},
         {t:'B',name:'Beta',sector:'Technology',size:50,perf:{'1D':0,'1W':null}}],
  ...clone(overrides)};
}
function harness(queue) {
 const timers=new Map(),intervals=[],events=[],calls=[];let id=0;
 const context={Promise,URL,Date,Number,JSON,Object,Array,Math,Error,TypeError,Set,AbortController,
  setInterval:fn=>{intervals.push(fn);return intervals.length;},
  setTimeout:fn=>{timers.set(++id,fn);return id;},clearTimeout:n=>timers.delete(n),
  fetch:async (url,options)=>{
   calls.push({url,options});if(!queue.length)throw new Error('No fixture response queued');
   const response=queue.shift(); if(response instanceof Error)throw response;
   if(typeof response==='function')return response(options);
   return {ok:true,status:200,json:async()=>clone(response)};
  },
  document:{hidden:false,dispatchEvent:event=>{events.push(event);if(context.onEvent)context.onEvent(event);}},
  CustomEvent:function(name,opts){this.type=name;this.detail=opts.detail;}
 };
 vm.createContext(context);
 let raw=fs.readFileSync(sourceFile(),'utf8');
 const start=raw.indexOf("  var JSON_URL =");
 const end=raw.indexOf('  /* ---- per-timeframe colour-scale floors',start);
 if(start<0||end<=start)throw new Error('Expected heatmap loader boundary missing');
 raw=raw.slice(start,end);
 vm.runInContext(raw+'\nglobalThis.api={loadData,startAutoRefresh};',context,{filename:sourceFile()});
 const url='marketdata/china_heatmap.json';
 return {context,events,calls,intervals,timers,queue,url,clone,
  load:u=>context.api.loadData(u||url),start:u=>context.api.startAutoRefresh(u||url),
  tick:async()=>{if(!intervals.length)throw new Error('No refresh owner');intervals[0]();await flush();},
  timeout:async()=>{for(const [i,fn] of [...timers]){timers.delete(i);fn();}await flush();},flush};
}
module.exports={harness,payload,clone,flush};
