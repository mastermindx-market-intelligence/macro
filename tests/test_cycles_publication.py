"""Publication coherence is stronger than a matching session label.

Use the real Python emitter and browser receiver in a Node VM with WebCrypto.
No market engine, live source, forward log or browser installation is needed.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from engine.sector_generation_guard import cycle_spine_identity
from engine.leadership_rotation_context import measured_group_read
from scripts._cycles_payload import publication_scripts

ROOT = Path(__file__).resolve().parents[1]


def payload():
    return {
        "meta": {"asOf": "2026-11-02", "region": "us", "benchmark": "SPY",
                 "xDomain": [2020, 2027], "today": 2026.84, "n_baskets": 1,
                 "families": [{"key": "baskets", "count": 1}]},
        "phases": {"Trough": {"hue": "green"}},
        "sectors": [{"id": "xle", "ticker": "XLE", "kind": "sector",
                     "name": "Energy (Equal-Weight)", "name_zh": "能源", "now": {"phase": "Trough"},
                     "price": [{"x": 2026.5, "v": 1e-7}, {"x": 2026.6, "v": 100.1}],
                     "osc": [{"x":2025,"v":20},{"x":2026,"v":40}], "turns": [{"x":2022,"date":"2022-01-03","k":"trough"},
                                            {"x":2024,"date":"2024-01-03","k":"peak"}], "rs_history": []}],
        "baskets": [{"id": "b-test", "kind": "basket", "now": {}, "price": [],
                     "osc": [{"x":2025,"v":10},{"x":2026,"v":30}]}],
    }


SOURCES = {"narr": {"status": "available", "records": 1}, "dna": {"status": "available", "records": 0}}


def bundle(data=None, narr=None):
    return publication_scripts(data or payload(), narr or {"xle": {"now": "dated research"}}, {}, sources=SOURCES)


def test_spine_detects_same_session_corrections_but_ignores_other_families():
    original = payload()
    stamp = cycle_spine_identity(original)
    changed = copy.deepcopy(original)
    changed["sectors"][0]["price"][0]["v"] = 0
    assert cycle_spine_identity(changed) != stamp
    changed = copy.deepcopy(original)
    changed["meta"]["n_baskets"] = 2
    changed["meta"]["families"] = []
    changed["baskets"].append({"id": "b-other", "price": [1]})
    assert cycle_spine_identity(changed) == stamp
    assert bundle(changed)["core"] != bundle(original)["core"]


def test_central_stamps_the_payload_it_actually_consumed():
    data = payload()
    expected = cycle_spine_identity(data)
    assert measured_group_read(data)["generation"]["cycle_spine"] == expected
    data["sectors"][0]["price"][0]["v"] = 2
    assert measured_group_read(data)["generation"]["cycle_spine"] != expected


@pytest.mark.parametrize("bad", ["duplicate_id", "duplicate_ticker", "nan", "date"])
def test_invalid_spine_is_unavailable(bad):
    data = payload()
    if bad.startswith("duplicate"):
        row = copy.deepcopy(data["sectors"][0])
        row["id" if bad == "duplicate_ticker" else "ticker"] = "other"
        data["sectors"].append(row)
    elif bad == "nan":
        data["sectors"][0]["now"]["pos"] = float("nan")
    else:
        data["meta"]["asOf"] = "2026-02-31"
    assert cycle_spine_identity(data) is None


def test_publication_is_deterministic_and_does_not_mutate_engine():
    data = payload()
    before = copy.deepcopy(data)
    assert bundle(data) == bundle(data)
    assert data == before
    assert bundle(data, {"xle": {"now": "revised research"}})["core"] != bundle(data)["core"]


def test_publication_rejects_cross_family_collisions_and_non_session_dates():
    data = payload()
    data["baskets"][0]["id"] = "xle"
    with pytest.raises(ValueError, match="unique entity ids"):
        bundle(data)
    data = payload()
    data["meta"]["asOf"] += "T16:00:00Z"
    assert cycle_spine_identity(data) is None
    with pytest.raises(ValueError, match="source session"):
        bundle(data)


NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert'),{webcrypto,createHash}=require('crypto');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const callbacks={},events=[],notifications=[],cancelled=[];
const document={readyState:'loading',documentElement:{getAttribute:()=> 'en'},
  getElementById:()=>null,querySelector:()=>null,querySelectorAll:()=>[],
  addEventListener:(name,fn)=>{(callbacks[name]||(callbacks[name]=[])).push(fn)},
  dispatchEvent:e=>{events.push(e.type);(callbacks[e.type]||[]).forEach(fn=>fn(e))},
  head:{appendChild:()=>{}},body:{style:{}}};
const c={document,console,crypto:webcrypto,TextEncoder,Uint8Array,URL,
  innerWidth:1440,location:{pathname:'/sector_cycles.html',search:'',hash:''},
  history:{state:{originNav:{id:'retained'}},replaceState:()=>{}},
  setTimeout:()=>0,clearTimeout:()=>{},requestAnimationFrame:fn=>fn(),cancelAnimationFrame:id=>cancelled.push(id),
  matchMedia:()=>({matches:false}),addEventListener:()=>{},
  CustomEvent:function(type,options){this.type=type;this.detail=options&&options.detail},
  SC_LAZY_EXTRAS:true};c.window=c;
let chart, familyClicks={};
if(input.visible){
 const chartNode={getBoundingClientRect:()=>({width:900}),addEventListener:()=>{}};
 document.getElementById=id=>id==='sc-chart'?chartNode:null;
 c.SectorCyclesHost={onState:s=>notifications.push(s),onFocus:()=>{}};
 const tabs=['sectors','baskets'].map(fam=>({getAttribute:k=>k==='data-fam'?fam:null,setAttribute(){},classList:{toggle(){}},
   addEventListener:(name,fn)=>{familyClicks[fam]=fn}}));
 document.querySelectorAll=selector=>selector==='#sc-tabs .sc-tab'?tabs:[];
 c.MMChart={create:(_,spec)=>(chart={spec,_tw:77,view:[2020,2027],
  setHidden(m){this.hidden=m},focus(id){this.focused=id},resize(){},update(s){this.spec=s},
  getView(){return this.view.slice()},setView(d){this.view=d.slice();this.spec.onZoom(d,false)}})};
}
vm.createContext(c);
vm.runInContext(input.scripts.core,c);
if(input.corruptCore)c.SECTOR_CYCLES_PUBLICATION.payload_json+=' ';
if(input.tamperManifest){c.SECTOR_CYCLES_PUBLICATION.manifest_json='{}';c.SECTOR_CYCLES_PUBLICATION.id='cycp1-'+createHash('sha256').update('{}').digest('hex');}
if(input.preload){vm.runInContext(input.scripts.narr,c);vm.runInContext(input.scripts.dna,c);c.SC_LAZY_EXTRAS=false;}
vm.runInContext(fs.readFileSync(input.renderer,'utf8'),c);
(callbacks.DOMContentLoaded||[]).forEach(fn=>fn());
const settle=()=>new Promise(r=>setTimeout(r,15));
(async()=>{
 await settle();
 if(input.corruptCore||input.tamperManifest){assert.equal(c.SectorCyclesEvidence().status,'integrity_failed');process.stdout.write('{}');return;}
 assert.equal(c.SectorCyclesEvidence().status,'verified');
 if(input.preload){assert.equal(c.SectorCyclesEvidence().parts.narr,'verified');assert.equal(c.SectorCyclesEvidence().parts.dna,'verified');}
 const record=c.SECTOR_CYCLES.sectors[0];
 vm.runInContext(input.scripts.series,c);
 const good=c.SECTOR_CYCLES_SERIES_PUBLICATION;
 c.SECTOR_CYCLES_SERIES_PUBLICATION={...good,publication_id:'cycp1-'+'f'.repeat(64)};
 await c.SectorCyclesHydrateSeries();
 assert.equal(c.SectorCyclesEvidence().parts.series,'incompatible_publication');
 assert.equal(record.price,undefined);
 c.SECTOR_CYCLES_SERIES_PUBLICATION={...good,namespace:'sector_cycles:china'};
 await c.SectorCyclesHydrateSeries();
 assert.equal(c.SectorCyclesEvidence().parts.series,'incompatible_publication');
 assert.equal(record.price,undefined);
 c.SECTOR_CYCLES_SERIES_PUBLICATION={...good,payload_json:good.payload_json.replace('100.1','100.2')};
 await c.SectorCyclesHydrateSeries();
 assert.equal(c.SectorCyclesEvidence().parts.series,'integrity_failed');
 assert.equal(record.price,undefined);
 c.SECTOR_CYCLES_SERIES_PUBLICATION=good;
 await c.SectorCyclesHydrateSeries();
 assert.equal(c.SectorCyclesEvidence().parts.series,'verified');
 assert.strictEqual(c.SECTOR_CYCLES.sectors[0],record);
 assert.equal(record.price[0].v,1e-7);
 assert.equal(record.name,'Energy');
 vm.runInContext(input.scripts.narr,c);vm.runInContext(input.scripts.dna,c);
 await c.SectorCyclesHydrateExtras();
 assert.equal(c.SectorCyclesEvidence().parts.narr,'verified');
 assert.equal(c.SectorCyclesEvidence().parts.dna,'verified');
 const receipt=c.SectorCyclesEvidence();
 // Execute the existing Central mini-chart consumer against the real receipt.
 const central=fs.readFileSync(input.central,'utf8');
 const mini=central.slice(central.indexOf('  var _cycSeriesCache'),central.indexOf('  function _decYearToYM'));
 c.D={sectors:[{id:'xle'}],baskets:[{id:'b-test'}],measured_read:{generation:{session_end:receipt.asOf,cycle_spine:receipt.spine}}};
 vm.runInContext("var lang=()=> 'en',L=(en)=>en,esc=(s)=>String(s);"+mini,c);
 assert.equal(c._cycSeries('xle').pts.at(-1).v,40);
 assert.ok(c.miniCycChart({id:'b-test'}).includes('Separate Cycles snapshot'));
 c.D.measured_read.generation.cycle_spine={...receipt.spine,sha256:'f'.repeat(64)};
 assert.equal(c._cycSeries('xle'),null,'cached points cannot bypass a changed Central spine');
 c.D.measured_read.generation.cycle_spine=receipt.spine;
 const request={id:'xle',asOf:'2026-11-02',requirePublication:true,spine:receipt.spine};
 assert.equal(c.SectorCyclesApply({...request,id:'b-test'}).reason,'unverified_family');
 assert.equal(c.SectorCyclesApply(request).status,input.visible?'applied':'pending');
 if(input.visible){
  const base=c.SectorCyclesCapture(), count=notifications.length;
  const advanced={...base,focus:'xle',mode:'price',scale:'linear',range:[2022,2024],phases:['Expansion'],leg:{start:'2022-01-03',end:'2024-01-03'}};
  const applied=c.SectorCyclesApply({...request,entryKey:'entry-A',snapshot:advanced});
  assert.equal(applied.restoration,'restored');
  assert.equal(chart.hidden.xle,false,'requested off-phase focus must be visible');
  assert.equal(chart.focused,'xle');assert.ok(cancelled.includes(77));
  assert.equal(notifications.length,count,'restore cannot write host navigation/state');
  assert.equal(c.SectorCyclesCapture().mode,'price');
  assert.deepEqual(c.SectorCyclesCapture().range,[2022,2024]);
  familyClicks.baskets();
  assert.equal(c.SectorCyclesCapture().focus,null);
  assert.equal(c.SectorCyclesCapture().leg,null,'actual family click must clear the prior sector leg');
  const clicked=c.SectorCyclesCapture();
  assert.equal(c.SectorCyclesApply({family:'baskets',entryKey:'family-click',snapshot:clicked}).restoration,'restored');
  c.SectorCyclesApply({id:null,family:'baskets',entryKey:'entry-B'});
  const empty={...c.SectorCyclesCapture(),selectedIds:[]};
  c.SectorCyclesApply({id:null,family:'baskets',entryKey:'entry-B-empty',snapshot:empty});
  assert.deepEqual(c.SectorCyclesCapture().selectedIds,[]);
  c.SectorCyclesApply({...request,entryKey:'entry-A',snapshot:advanced});
  assert.equal(c.SectorCyclesCapture().scale,'linear');
  (callbacks.langchange||[]).forEach(fn=>fn());
  await c.SectorCyclesHydrateExtras();await c.SectorCyclesHydrateSeries();
  assert.deepEqual(c.SectorCyclesCapture().leg,advanced.leg,'hydration/language preserve stable leg identity');
  assert.deepEqual(c.SectorCyclesCapture().range,advanced.range);
  c.SectorCyclesApply({...request,entryKey:'entry-same-url-fresh'});
  assert.equal(c.SectorCyclesCapture().mode,'osc','new entry must not inherit the previous settings');
  const stale={...advanced,publicationId:'cycp1-'+'0'.repeat(64)};
  assert.equal(c.SectorCyclesApply({...request,entryKey:'entry-stale',snapshot:stale}).restoration,'source_changed');
  assert.equal(c.SectorCyclesCapture().mode,'osc');
  // Strict external restoration must reject before fallback or any settings mutation.
  const stable=JSON.stringify(c.SectorCyclesCapture());
  for(const snapshot of [
    {...advanced,publicationId:'cycp1-'+'0'.repeat(64)},
    {...advanced,range:[2024,2022]},
    {...advanced,region:'china'},
    {...advanced,phases:['Expansion','Expansion']},
    {...advanced,selectedIds:['xle']},
    {...advanced,leg:{start:'missing',end:'missing'}},
  ]){
    const strict=c.SectorCyclesApply({...request,entryKey:'strict-reject',strictRestore:true,restore:true,snapshot});
    assert.equal(strict.status,'rejected');
    assert.equal(JSON.stringify(c.SectorCyclesCapture()),stable,'strict refusal leaves current settings intact');
  }
  const portable={...advanced,leg:null};
  assert.equal(c.SectorCyclesApply({...request,strictRestore:true,validateOnly:true,snapshot:portable}).status,'validated');
  assert.equal(JSON.stringify(c.SectorCyclesCapture()),stable,'validation itself has no settings effects');
  assert.equal(c.SectorCyclesApply({...request,entryKey:'strict-valid',strictRestore:true,restore:true,snapshot:portable}).status,'applied');
  assert.equal(c.SectorCyclesCapture().mode,'price');
  assert.deepEqual(c.SectorCyclesCapture().range,[2022,2024]);
  const malformed={...advanced,range:[2024,2022]};
  assert.equal(c.SectorCyclesApply({...request,entryKey:'entry-malformed',snapshot:malformed}).restoration,'invalid_state');
 }
 request.spine={...receipt.spine,sha256:'0'.repeat(64)};
 assert.equal(c.SectorCyclesApply(request).status,'source_mismatch');
 const oldPrice=record.price;
 const pending=c.SectorCyclesHydrateSeries();
 c.SECTOR_CYCLES={...c.SECTOR_CYCLES}; // a replacement publication supersedes this renderer
 await pending;
 assert.strictEqual(record.price,oldPrice);
 assert.equal(c.SectorCyclesApply({id:'xle'}).status,'source_mismatch');
 assert.equal(c.SectorCyclesEvidence().status,'superseded');
 assert.equal(c.SectorCyclesEvidence().spine,null);
 assert.equal(c._cycSeries('xle'),null,'a superseded core cannot reuse a verified mini-chart cache');
 process.stdout.write(JSON.stringify({events,receipt}));
})().catch(e=>{console.error(e);process.exitCode=1});
"""


@pytest.mark.parametrize("visible,corrupt_core,tamper_manifest,preload", [
    (False,False,False,False),(True,False,False,False),(False,True,False,False),
    (False,False,True,False),(False,False,False,True)])
def test_real_emitter_and_receiver_reject_mixed_and_corrupt_parts(visible,corrupt_core,tamper_manifest,preload):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to execute the real browser receiver")
    result = subprocess.run([node, "-e", NODE], input=json.dumps({"scripts": bundle(), "visible":visible,"corruptCore":corrupt_core,"tamperManifest":tamper_manifest,"preload":preload,
                            "renderer": str(ROOT / "templates/sector_cycles.js"),"central": str(ROOT / "templates/sector_central.html.j2")}),
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    if not corrupt_core and not tamper_manifest:
        receipt = json.loads(result.stdout)["receipt"]
        assert receipt["status"] == "verified"
        assert receipt["parts"]["series"] == "verified"


def test_three_regional_builders_use_the_same_publication_serializer():
    for name in ("build_sector_cycles.py", "build_china_sector_cycles.py", "build_country_cycles.py"):
        source = (ROOT / "scripts" / name).read_text()
        assert "publication_scripts(data, narr, dna, sources=sources" in source
        assert 'receipt.update(publication_receipt(res))' in source
