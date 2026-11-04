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
  replaceState(s,_,u){shared.entries[shared.at]={url:new URL(u===undefined?context.location.href:u,context.location).href,state:s}},
  pushState(s,_,u){shared.entries.splice(shared.at+1);shared.entries.push({url:new URL(u===undefined?context.location.href:u,context.location).href,state:s});shared.at++},
  back(){shared.backCalls++;travel(-1)},forward(){travel(1)}};
 context={document:doc,history,URL,URLSearchParams,TextEncoder,scrollY:650,scrollTo(x,y){this.scrollY=y},
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
   return {status,id:c.id||null,family:c.family||'sectors',asOf:'2026-11-02',series:'ready',publication:{status:'verified'}};
  }};
 context.window=context;vm.runInNewContext(source,context);
 const api={c:context,doc,opener,nodes,applied,
  tick(){frames.splice(0).forEach(f=>f())},
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


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required")
@pytest.mark.parametrize("intent", ["pointerdown", "touchstart", "wheel", "keydown"])
def test_user_intent_supersedes_exact_entry_and_fallback_viewport_replay(intent):
    checks = r"""
// Quiet navigation restores the entry's actual scroll and typed focus target.
function queueExact(){
 const entry={...a.c.history.state.siWorkspace,viewport:{scrollY:120,focus:{kind:'board-cycle-opener',id:'xle'}}};
 a.c.history.replaceState({...a.c.history.state,siWorkspace:entry},'',a.c.location.href);
 a.c.scrollY=900;a.doc.activeElement=a.nodes['sc-cycle-heading'];a.c.__siRoute();
}
queueExact();a.flush();assert.equal(a.c.scrollY,120);assert.equal(a.doc.activeElement,a.opener);
// A later user's input/focus is not overwritten by the two delayed frames.
queueExact();a.event(INTENT);a.flush();
assert.equal(a.c.scrollY,900,'late exact-entry replay moved the user');
assert.equal(a.doc.activeElement,a.nodes['sc-cycle-heading'],'late replay stole focus');
// The old per-view fallback has the same cancellation rule.
a.c.history.replaceState({...a.c.history.state,siWorkspace:{...a.c.history.state.siWorkspace,viewport:null}},'',a.c.location.href);
a.c.scrollY=310;a.c.__siRoute();a.c.scrollY=777;a.event(INTENT);a.flush();
assert.equal(a.c.scrollY,777,'late per-view fallback moved the user');
"""
    result = subprocess.run(
        ["node", "-e", HOST + checks.replace("INTENT", repr(intent)), str(ROOT / "templates/si_workspace.js")],
        text=True, capture_output=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required")
def test_export_is_detached_bounded_pure_and_current_entry_publication_owned():
    checks = r"""
const publication='cycp1-'+'a'.repeat(64);
let proof={status:'verified',publicationId:publication,region:'us'};
a.c.SectorCyclesEvidence=()=>proof;
a.c.SectorCentralOpenCycle('xle',a.opener);
assert.equal(a.c.SectorWorkspaceExport(),null,'source-rejected chart is not current exportable state');
a.click('sc-cycle-latest');
const native={schema:'sector_cycles.view.v1',publicationId:publication,region:'us',family:'sectors',focus:'xle',
 mode:'price',scale:'linear',range:[2022,2024],phases:['Expansion'],selectedIds:[],
 mobileSelection:{mode:'leaders',ids:[]},leg:{start:'2022-01-03',end:'2024-01-03'}};
a.state(native);
const foreign={dom:a.doc};foreign.circular=foreign;
a.c.history.replaceState({...a.c.history.state,ownerPrivate:foreign,
 siWorkspace:{...a.c.history.state.siWorkspace,private:foreign},
 siCyclesOrigin:{...a.c.history.state.siCyclesOrigin,originNav:foreign}},'',a.c.location.href);
const priorState=a.c.history.state, priorEntry=priorState.siWorkspace;
const exported=a.c.SectorWorkspaceExport();assert.ok(exported);
assert.strictEqual(a.c.history.state,priorState);assert.strictEqual(priorState.siWorkspace,priorEntry);
assert.deepEqual(Object.keys(exported).sort(),['siCyclesOrigin','siWorkspace']);
assert.ok(!JSON.stringify(exported).includes('ownerPrivate'));assert.ok(!JSON.stringify(exported).includes('originNav'));
assert.equal(exported.siCyclesOrigin.entry.view,'map');
const originalMeasured=priorState.siCyclesOrigin.entry.measured.historyMode;
exported.siWorkspace.cycles.range[0]=1900;exported.siWorkspace.cycles.phases.push('Trough');
exported.siWorkspace.cycles.leg.start='changed';exported.siCyclesOrigin.entry.measured.historyMode='changed';
assert.deepEqual(a.chart(),native);assert.equal(priorState.siCyclesOrigin.entry.measured.historyMode,originalMeasured);
// A bridge flush calls only the pure export, even when existing capture persists.
let writes=0,flushes=0;
const replace=a.c.history.replaceState;
a.c.history.replaceState=function(...args){assert.ok(++writes<3,'recursive history flush');flushes++;assert.ok(a.c.SectorWorkspaceExport());return replace.apply(this,args)};
a.c.SectorWorkspaceExport();assert.equal(writes,0);
a.c.SectorWorkspaceCapture();assert.equal(writes,1);assert.equal(flushes,1);
a.c.history.replaceState=replace;
// Same URL is insufficient: a newly owned history entry requires activation.
const owned=a.c.history.state;
a.c.history.replaceState({...owned,siWorkspace:{...owned.siWorkspace,entryId:'other-entry'}},'',a.c.location.href);
assert.equal(a.c.SectorWorkspaceExport(),null);
a.c.history.replaceState(owned,'',a.c.location.href);
proof={...proof,publicationId:'cycp1-'+'b'.repeat(64)};
assert.equal(a.c.SectorWorkspaceExport(),null,'same-date source replacement cannot export the old chart');
proof={...proof,publicationId:publication,status:'superseded'};assert.equal(a.c.SectorWorkspaceExport(),null);
proof={...proof,status:'verified'};
// Malformed and oversized native snapshots cannot leak arbitrary payloads.
a.state({...native,selectedIds:Array(513).fill('x')});assert.equal(a.c.SectorWorkspaceExport(),null);
a.state({...native,selectedIds:Array(120).fill('界'.repeat(100))});assert.equal(a.c.SectorWorkspaceExport(),null,'32KiB bound is UTF-8, not character count');
a.state({...native,range:[NaN,2024]});assert.equal(a.c.SectorWorkspaceExport(),null);
a.state(native);
const origin=a.c.history.state.siCyclesOrigin;
a.c.history.replaceState({...a.c.history.state,siCyclesOrigin:{...origin,entry:{...origin.entry,href:'/wrong.html#map'}}},'',a.c.location.href);
assert.equal(a.c.SectorWorkspaceExport().siCyclesOrigin.entry,null,'a valid URL does not validate its attached snapshot');
a.c.history.replaceState({...a.c.history.state,siCyclesOrigin:{href:'https://foreign.example/'}},'',a.c.location.href);
assert.equal(a.c.SectorWorkspaceExport().siCyclesOrigin,null);
"""
    result = subprocess.run(
        ["node", "-e", HOST + checks, str(ROOT / "templates/si_workspace.js")],
        text=True, capture_output=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required")
def test_external_restore_is_current_entry_bound_validated_once_and_cancellable():
    checks = r"""

// Apply the native projection to the existing destination without routing or replacing its identity.
a.flush();
const saved=a.c.SectorWorkspaceExport();
assert.ok(saved&&saved.siWorkspace.view==='map');
saved.siWorkspace.entryId='captured-source-entry';
saved.siWorkspace.viewport={scrollY:120,focus:{kind:'board-cycle-opener',id:'xle'}};
saved.siWorkspace.measured.historyMode='obs';
const dest=a.c.history.state.siWorkspace.entryId,where=a.c.location.href;
let urlWrites=0,results=[];
const replace=a.c.history.replaceState;
a.c.history.replaceState=function(state,title,url){if(arguments.length>2)urlWrites++;return replace.call(this,state,title,url);};
a.c.scrollY=900;
const options={restoreId:'restore-map-1',snapshotId:'parent-entry:2',expectedHref:a.c.location.pathname+a.c.location.search+a.c.location.hash,
 onResult:r=>results.push(copy(r))};
assert.equal(a.c.SectorWorkspaceApplyCurrent(saved,options).status,'pending');
a.flush();
assert.equal(results.length,1);assert.equal(results[0].status,'applied');
assert.equal(results[0].scope,'serialized_entry_settings');
assert.equal(a.c.scrollY,120);assert.equal(a.doc.activeElement,a.opener);
assert.equal(a.c.history.state.siWorkspace.entryId,dest);
assert.equal(a.c.history.state.originNav.source,'market');
assert.equal(a.c.location.href,where);assert.equal(urlWrites,0,'restore bookkeeping omits URL');
assert.equal(a.c.SectorWorkspaceApplyCurrent(saved,options).status,'applied');
assert.equal(results.length,1,'duplicate operation never reapplies or acknowledges twice');
const invalid=copy(saved);invalid.extra='foreign';
assert.equal(a.c.SectorWorkspaceApplyCurrent(invalid,{...options,restoreId:'bad-shape'}).status,'rejected');
assert.equal(a.c.location.href,where);
const badGeneration=copy(saved);badGeneration.siWorkspace.measured.generation='old-generation';
results=[];a.c.SectorWorkspaceApplyCurrent(badGeneration,{...options,restoreId:'bad-measured'});a.flush();
assert.equal(results[0].status,'rejected');assert.equal(results[0].reason,'measured_source_changed');
results=[];
a.c.SectorWorkspaceApplyCurrent(saved,{...options,restoreId:'interrupt-map'});
a.tick();a.c.scrollY=950;a.event('wheel');a.flush();
assert.equal(results[0].status,'partial');assert.equal(results[0].reason,'user_input');
assert.equal(a.c.scrollY,950,'late animation-frame replay cannot overwrite new user intent');
// Pending source admission is tied to this exact native child entry.
a.c.history.pushState({originNav:{source:'market'}},'','/sector_central.html?g=XLE&cycle=xle&cycleSource=latest#cycles');
a.c.__siRoute();a.flush();
let proof={status:'pending',publicationId:'cycp1-'+'a'.repeat(64),region:'us'},appliedCount=0;
const cycle={schema:'sector_cycles.view.v1',publicationId:proof.publicationId,region:'us',family:'sectors',focus:'xle',
 mode:'price',scale:'linear',range:[2022,2024],phases:['Expansion'],selectedIds:[],
 mobileSelection:{mode:'leaders',ids:[]},leg:null};
let actual={...cycle,mode:'osc',scale:'log'};
a.c.SectorCyclesCapture=()=>copy(actual);
a.c.SectorCyclesEvidence=()=>copy(proof);
a.c.SectorCyclesApply=c=>{
 if(c.validateOnly)return {status:'validated'};
 if(c.restore){actual=copy(c.snapshot);appliedCount++;}
 return {status:'applied',id:'xle',family:'sectors',leg:'closed',publication:copy(proof)};
};
const incoming={siWorkspace:{...copy(a.c.history.state.siWorkspace),measured:a.c.SectorMeasuredCapture(),cycles:cycle,
 viewport:{scrollY:220,focus:null}},siCyclesOrigin:null};
incoming.siWorkspace.entryId='captured-cycle-entry';
const cycleOptions={restoreId:'pending-cycle',snapshotId:'parent-cycle:3',expectedHref:incoming.siWorkspace.href,
 onResult:r=>results.push(copy(r))};
results=[];a.c.SectorWorkspaceApplyCurrent(incoming,cycleOptions);
assert.equal(results.length,0);assert.equal(appliedCount,0);
a.event('keydown');proof.status='verified';a.event('sc:publication-ready');a.flush();
assert.equal(appliedCount,0);assert.equal(results[0].status,'rejected');
results=[];a.c.SectorWorkspaceApplyCurrent(incoming,{...cycleOptions,restoreId:'verified-cycle'});a.flush();
assert.equal(results[0].status,'applied');assert.equal(appliedCount,1);
assert.equal(results[0].publicationId,cycle.publicationId);
assert.notEqual(a.c.history.state.siWorkspace.entryId,'captured-cycle-entry');
a.event('sc:series-ready');a.flush();assert.equal(appliedCount,1,'later hydration does not replay the restore');
results=[];a.c.SectorWorkspaceApplyCurrent(incoming,{...cycleOptions,restoreId:'superseded-during-viewport'});
a.tick();proof={...proof,publicationId:'cycp1-'+'b'.repeat(64)};a.flush();
assert.equal(results[0].status,'partial');assert.equal(results[0].reason,'source_or_settings_changed');

"""
    result = subprocess.run(["node", "-e", HOST + checks, str(ROOT / "templates/si_workspace.js")],
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
