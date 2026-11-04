"""Execute the real Central host with a browser-like entry stack.

The renderer's actual capture/apply behavior is tested with WebCrypto in
test_cycles_publication.py. This boundary test isolates host custody of entries,
source policy, foreign history state and typed return focus; it is not visual QA.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]

HOST = r"""
const vm=require('vm'),fs=require('fs'),assert=require('assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const copy=x=>JSON.parse(JSON.stringify(x));
const shared={entries:[{url:'https://fixture.test/sector_central.html?g=XLE&universe=us#map',state:{originNav:{source:'market'},mr:'XLE'}}],at:0,backCalls:0};
let active;
function boot(){
 const dl={},wl={},frames=[],nodes={},applied=[];
 let context,chart={mode:'osc',scale:'log',range:[2020,2027]},rendererEntry=null,measured='obs';
 function el(id,attrs={}){return {id,hidden:false,dataset:{},attrs,isConnected:true,
  classList:{toggle(){}},getAttribute(k){return this.attrs[k]||null},setAttribute(k,v){this.attrs[k]=v},removeAttribute(){},
  getBoundingClientRect:()=>({width:900}),addEventListener(){},closest(s){return s==='.si-view'?{}:null},
  focus(){doc.activeElement=this}};}
 ['sc-cycle-status','sc-native-study','sc-cycle-return','sc-cycle-latest','sc-cycle-heading'].forEach(id=>nodes[id]=el(id));
 const opener=el('board-opener',{'data-focus':'xle'});
 const views=['overview','map','cycles','moving','money','explore','confluence'].map(id=>el(id,{'data-view':id}));
 const doc={title:'Sector Intelligence',documentElement:{getAttribute:()=> 'en'},activeElement:opener,
  getElementById:id=>nodes[id]||null,
  querySelectorAll:s=>s==='.si-view'?views:s==='.si-view.on [data-focus]'?[opener]:[],
  querySelector:s=>s.includes('si-view[data-view')?views.find(v=>s.includes(v.id)):null,
  createElement:()=>el('script'),head:{appendChild(){}},
  addEventListener:(n,f)=>(dl[n]||=[]).push(f),dispatchEvent:e=>(dl[e.type]||[]).forEach(f=>f(e))};
 const history={get state(){return shared.entries[shared.at].state},get length(){return shared.entries.length},
  replaceState(s,_,u){shared.entries[shared.at]={url:new URL(u,context.location).href,state:s}},
  pushState(s,_,u){shared.entries.splice(shared.at+1);shared.entries.push({url:new URL(u,context.location).href,state:s});shared.at++},
  back(){shared.backCalls++;travel(-1)},forward(){travel(1)}};
 context={document:doc,history,URL,URLSearchParams,scrollY:650,scrollTo(x,y){this.scrollY=y},
  get location(){return new URL(shared.entries[shared.at].url)},
  crypto:{randomUUID:()=> 'entry-'+(++shared.seq)},
  Event:class{constructor(type){this.type=type}},CustomEvent:class{constructor(type,o={}){this.type=type;this.detail=o.detail}},
  requestAnimationFrame:f=>frames.push(f),addEventListener:(n,f)=>(wl[n]||=[]).push(f),dispatchEvent(){},
  SECTOR_CENTRAL:{measured_read:{generation:{session_end:'2026-10-30',cycle_spine:{sha256:'source-a'}}}},
  SectorMeasuredCapture:()=>({schema:'sector_central.measured_view.v1',groupId:'XLE',historyMode:measured,generation:'source-a'}),
  SectorMeasuredApply:s=>{measured=s&&s.historyMode||'recon'},
  SectorCyclesCapture:()=>copy(chart),
  SectorCyclesApply:c=>{
   applied.push(copy(c));
   const status=c.asOf&&c.asOf!=='2026-11-02'?'source_mismatch':'applied';
   if(status==='applied'&&c.entryKey!==rendererEntry){chart=copy(c.snapshot||{mode:'osc',scale:'log',range:[2020,2027]});rendererEntry=c.entryKey;}
   return {status,asOf:'2026-11-02',series:'ready',publication:{status:'verified'}};
  }};
 context.window=context;vm.runInNewContext(source,context);
 const api={c:context,doc,opener,nodes,applied,
  flush(){let n=0;while(frames.length){assert.ok(n++<20);frames.splice(0).forEach(f=>f())}},
  fire(n){(wl[n]||[]).forEach(f=>f({}));},
  event(n){doc.dispatchEvent({type:n})},
  click(id){const target={closest:s=>s==='#'+id?nodes[id]:null};(dl.click||[]).forEach(f=>f({target,button:0,preventDefault(){}}));},
  state(s){chart=copy(s);context.SectorCyclesHost.onState(copy(s))},
  chart:()=>copy(chart),measured:()=>measured};
 active=api;return api;
}
function travel(n){shared.at+=n;assert.ok(shared.at>=0&&shared.at<shared.entries.length);active.fire('popstate');active.fire('hashchange');active.flush()}
shared.seq=0;
let a=boot();
a.c.SectorCentralOpenCycle('xle',a.opener);
assert.equal(a.nodes['sc-cycle-status'].dataset.state,'source_mismatch');
assert.equal(a.nodes['sc-cycle-latest'].hidden,false);
a.click('sc-cycle-latest');
const A={mode:'price',scale:'linear',range:[2022,2024]};a.state(A);
const href=a.c.location.href, aid=a.c.history.state.siWorkspace.entryId;
// A late focus-save queued under A cannot overwrite a newly pushed B entry.
a.event('focusin');
a.c.history.pushState({originNav:{source:'market'}},'',href);a.c.__siRoute();
assert.notEqual(a.c.history.state.siWorkspace.entryId,aid);
assert.equal(a.chart().mode,'osc','fresh same-URL entry uses its own defaults');
const B={mode:'osc',scale:'log',range:[2024,2026]};a.state(B);a.flush();
assert.deepEqual(a.c.history.state.siWorkspace.cycles,B);
travel(-1);assert.deepEqual(a.chart(),A);
travel(1);assert.deepEqual(a.chart(),B);
// New document/runtime, same browser entry state.
a=boot();a.flush();assert.deepEqual(a.chart(),B);assert.equal(a.c.history.state.originNav.source,'market');
// Return uses its validated local origin; it never guesses history adjacency.
travel(-1);const before=shared.backCalls;a.click('sc-cycle-return');a.flush();
assert.equal(shared.backCalls,before);assert.equal(a.c.location.hash,'#map');
assert.equal(a.doc.activeElement,a.opener);assert.equal(a.measured(),'obs');
// General Cycles → in-chart selection retains its own dated source on refresh.
a.c.history.pushState({originNav:{source:'market'}},'','/sector_central.html?g=XLE#cycles');a.c.__siRoute();
a.c.SectorCyclesHost.onFocus('xle','sectors');
assert.equal(a.c.location.searchParams.get('cycleSource'),'latest');
a.event('langchange');a.event('sc:series-ready');
assert.equal(a.nodes['sc-cycle-status'].dataset.state,'applied');
assert.equal(a.applied.at(-1).asOf,null);
// Foreign/copy-corrupted return state never authorizes a foreign destination.
a.c.history.replaceState({...a.c.history.state,siCyclesOrigin:{href:'https://foreign.example/'}},'',a.c.location.href);
a.click('sc-cycle-return');a.flush();assert.equal(a.c.location.origin,'https://fixture.test');
assert.equal(a.c.location.hash,'#map');assert.equal(a.c.history.state.originNav.source,'market');
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required")
def test_real_host_preserves_entry_state_source_policy_and_return_custody():
    result = subprocess.run(["node", "-e", HOST, str(ROOT / "templates/si_workspace.js")],
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
