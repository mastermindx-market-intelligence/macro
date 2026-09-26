'use strict';
// Research-only execution of selected existing client functions. No network/DOM/auth.
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[2], 'utf8');
const backend = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const flush = () => new Promise(resolve => setImmediate(resolve));
function harness(items) {
  let input = '', timerId = 0;
  const timers = new Map(), pending = [], renders = [];
  const c = {LANE:'latest', FILT:{inst:'',side:'',theme:'',q:''}, SEARCH_HITS:null,
    API:'', DocState:{isSaved:()=>false}, $:id => ({value:input}),
    setTimeout:fn => {timers.set(++timerId,fn); return timerId;},
    clearTimeout:id => timers.delete(id), withAuth:()=>Promise.resolve({}),
    fetch:url=>new Promise(resolve=>pending.push({url,resolve})),
    renderFeed:()=>renders.push(items.filter(x=>Boolean(c.matchItem(x))).map(x=>x.id))};
  vm.createContext(c); vm.runInContext(source,c,{timeout:1000});
  return {c, pending, renders, async start(q) {input=q;c.onSearchInput();
      for(const [id,fn] of [...timers]) {timers.delete(id);fn();}await flush();},
    async deliver(i,body,ok=true) {pending[i].resolve({ok,json:()=>Promise.resolve(body)});await flush();await flush();},
    visible:()=>items.filter(x=>Boolean(c.matchItem(x))).map(x=>x.id)};
}
function item(id,title,inst='DeskA',tickers=[]) {
  return {id,title,inst,tickers,desk:'',side:'sell',points:[],tags:[],top:false};
}
(async()=>{
 const out=[];
 let h=harness([item('metadata-only','Equipment outlook','DeskA',['ACMEQ'])]);
 await h.start('ACMEQ');const before=h.visible();await h.deliver(0,backend.metadata_only);
 out.push({id:'R8-G1',class:'gap',question:'Ticker-only discovery survives successful server response',
  expected:['metadata-only'],actual:h.visible(),before,server:backend.metadata_only});
 h=harness([item('literal','ACMEQ business outlook')]);await h.start('ACMEQ');
 await h.deliver(0,backend.no_connection);
 out.push({id:'R8-G3',class:'gap',question:'Unavailable response remains distinguishable from authoritative empty result',
  expected_search_hits_null:true,actual_search_hits_null:h.c.SEARCH_HITS===null,
  actual_visible:h.visible(),response:backend.no_connection});
 h=harness([item('literal','ACMEQ business outlook')]);await h.start('ACMEQ');
 await h.deliver(0,null,false);
 out.push({id:'R8-C5',class:'control',question:'HTTP failure retains local fallback',
  expected:['literal'],actual:h.visible()});
 h=harness([item('literal','ACMEQ business outlook')]);await h.start('ACMEQ');
 await h.deliver(0,backend.healthy_empty);
 out.push({id:'R8-C6',class:'control',question:'Successful empty response does not widen through local union',expected:[],actual:h.visible()});
 h=harness([item('old','ACMEQ older match','DeskA'),item('new','ACMEQ newer match','DeskB')]);
 h.c.FILT.inst='DeskA';await h.start('ACMEQ');h.c.FILT.inst='DeskB';await h.start('ACMEQ');
 await h.deliver(1,{items:[{id:'new'}],available:true});const newest=h.visible();
 await h.deliver(0,{items:[{id:'old'}],available:true});
 out.push({id:'R8-G5',class:'gap',question:'Late prior response cannot overwrite same-query/new-facet result',
  expected:['new'],actual:h.visible(),after_new_response:newest,request_urls:h.pending.map(x=>x.url)});
 h=harness([item('new','BETAQ outlook')]);await h.start('ACMEQ');await h.start('BETAQ');
 await h.deliver(1,{items:[{id:'new'}],available:true});await h.deliver(0,{items:[],available:true});
 out.push({id:'R8-C7',class:'control',question:'Changed-query stale response is rejected',expected:['new'],actual:h.visible()});
 for(const x of out) {
   x.requirement_met='expected' in x ? JSON.stringify(x.expected)===JSON.stringify(x.actual)
     : x.expected_search_hits_null===x.actual_search_hits_null;
 }
 process.stdout.write(JSON.stringify({runtime:process.version,scope:'Node VM; controlled fetch/timer/UI/auth fixtures; no browser or live API',cases:out},null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
