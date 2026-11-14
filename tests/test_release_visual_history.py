"""Source-truth, calculation, and existing Events-dialog integration contracts.

No live source fetch, no simulated street-surprise history and no trading claims.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import json

import pandas as pd
import pytest

from engine import release_visual_history as visual

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-11-13T15:00:00Z"


def _frame(*, duplicate: bool = False, gap: bool = False):
    first = date(2025, 1, 1)
    rows = []
    for i in range(19):
        year = first.year + (first.month - 1 + i) // 12
        month = (first.month - 1 + i) % 12 + 1
        period = f"{year:04d}-{month:02d}-01"
        if gap and i == 14:
            continue
        rows.append({"period": pd.Timestamp(period), "realtime_start": pd.Timestamp("2026-10-01"),
                     "realtime_end": date(9999,12,31), "value": 100.0 + i})
    # The expired historical revision is not selected for the chart.
    rows.append({"period": pd.Timestamp("2026-01-01"), "realtime_start": pd.Timestamp("2026-09-01"),
                 "realtime_end": date(2026,9,30), "value": 999.0})
    # The future revision cannot leak backwards to the collector's source clock.
    rows.append({"period": pd.Timestamp("2026-01-01"), "realtime_start": pd.Timestamp("2026-11-01"),
                 "realtime_end": date(9999,12,31), "value": 888.0})
    if duplicate:
        rows.append(dict(rows[12], realtime_start=pd.Timestamp("2026-09-30"), value=150.0))
    return pd.DataFrame(rows)


def _manifest(root, *, collected="2026-11-13T14:00:00Z", content=b"fake-parquet"):
    path=root/"data/fred_vintage/release_targets/PPIFIS_all_vintages.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    manifest={"schema":"release_target_vintage_collection.v1", "source_output_type":2,
              "integrity_profile":"release_target_artifact_sha256_bytes.v1",
              "status":"ok", "completed_at":collected,
              "series":{"PPIFIS":{"path":"data/fred_vintage/release_targets/PPIFIS_all_vintages.parquet",
                                "status":"written", "artifact_bytes":len(content),
                                "artifact_sha256":sha256(content).hexdigest()}}}
    (path.parent/"manifest.json").write_text(json.dumps(manifest))
    return path


def test_monthly_and_annual_rates_are_distinct_and_not_bps():
    levels={f"2025-{i:02d}":100.0 for i in range(1,13)}
    levels.update({"2026-01":110.0,"2026-02":110.5,"2026-03":111.0})
    yoy=visual._change(levels,12)
    mom=visual._change(levels,1)
    assert yoy == [{"period":"2026-01","value":10.0},
                   {"period":"2026-02","value":10.5},
                   {"period":"2026-03","value":11.0}]
    assert mom[-1]["value"] == round(100*(111.0/110.5-1),3)
    # A prior-month acceleration is 0.5 percentage point, not a 0.5% release surprise.
    assert round(yoy[-1]["value"]-yoy[-2]["value"],2) == 0.5


def test_source_asof_vintage_never_reads_future_or_expired_revisions():
    curve=visual._frame_points(_frame(),date(2026,10,16))
    assert curve["yoy"][0]["period"] == "2026-01"
    assert curve["yoy"][0]["value"] == 12.0
    assert curve["yoy"][-1]["period"] == "2026-07"
    assert curve["yoy"][-1]["value"] == round(100*(118/106-1),3)
    assert curve["mom"][-1]["period"] == "2026-07"
    assert all(x["value"] < 100 for x in curve["yoy"])


def test_overlapping_active_vintages_refused():
    with pytest.raises(ValueError,match="overlapping_active_vintages"):
        visual._frame_points(_frame(duplicate=True), date(2026,10,16))


def test_missing_months_not_interpolated():
    curve=visual._frame_points(_frame(gap=True),date(2026,10,16))
    yoy={p["period"] for p in curve["yoy"]}
    assert "2026-03" not in yoy
    assert "2026-04" in yoy


def test_missing_manifest_is_explicit_unavailable(tmp_path):
    result=visual.build_release_visual_history(tmp_path,asof=NOW)
    assert result["status"]=="unavailable"
    assert result["series"]==[]
    assert result["reason_codes"]
    assert result["display_only"] is True and not any(result["authority"].values())


def test_real_manifest_fence_partial_coverage_and_staleness(tmp_path,monkeypatch):
    _manifest(tmp_path,collected="2026-10-16T18:00:00Z")
    monkeypatch.setattr(visual,"load_full_vintage_parquets",lambda *a, **k:_frame())
    result=visual.build_release_visual_history(tmp_path,asof=NOW)
    assert result["status"]=="partial"
    assert result["source_status"]=="stale"
    assert "source_history_collection_stale" in result["reason_codes"]
    ppi=next(s for s in result["series"] if s["release"]=="ppi_finaldemand")
    assert ppi["status"]=="available" and len(ppi["yoy"])==7
    assert ppi["first_prints"]==[]  # no fabricated official receipts
    assert all(x["status"]=="unavailable" for x in result["series"][1:])


def test_wrong_digest_refuses_even_if_parquet_can_load(tmp_path,monkeypatch):
    path=_manifest(tmp_path)
    path.write_bytes(b"new-bytes-without-updating-manifest")
    called=[]
    monkeypatch.setattr(visual,"load_full_vintage_parquets",lambda *a, **k:called.append(1))
    result=visual.build_release_visual_history(tmp_path,asof=NOW)
    assert result["status"]=="unavailable"
    assert "ppi_finaldemand:vintage_manifest_integrity_mismatch" in result["reason_codes"]
    assert not called


def test_future_manifest_refused(tmp_path):
    _manifest(tmp_path,collected="2026-11-14T15:00:00Z")
    result=visual.build_release_visual_history(tmp_path,asof=NOW)
    assert result["status"]=="unavailable"
    assert "future_collection_clock" in result["reason_codes"]


def test_component_uses_original_radar_fetch_and_visible_dialog():
    template=(ROOT/"templates/dashboard.html.j2").read_text()
    script=(ROOT/"templates/release_visual_history.js").read_text()
    partial=(ROOT/"templates/_release_visual_history.html.j2").read_text()
    producer=(ROOT/"scripts/build_release_forecast.py").read_text()
    assert template.count('include "_release_visual_history.html.j2"')==1
    assert template.count('include "_release_surprise_confirmation.html.j2"')<=1
    assert template.index('id="rr-inline"') < template.index('include "_release_visual_history.html.j2"')
    assert 'window.MMXReleaseVisualHistory.render(' in template
    assert 'd && d.release_visual_history' in template
    assert "fetch('macrodata/release_forecast.json'" in template
    assert '"release_visual_history": release_visual_history' in producer
    assert '"release_forecast.v2"' in producer
    for forbidden in ("fetch(", "setInterval(", "localStorage", "sessionStorage", ".innerHTML", "eval("):
        assert forbidden not in script
    assert 'display_raw_allowed===true' in script
    assert "No verified pre-release economist poll" in script
    assert '<svg data-rrh-chart' in partial
    assert '<details class="mx-disc">' in partial
    assert 'class="l-en"' in partial and 'class="l-zh"' in partial


def test_native_jinja_partial_compiles():
    from jinja2 import Environment, FileSystemLoader
    env=Environment(loader=FileSystemLoader(str(ROOT/"templates")))
    markup=env.get_template("_release_visual_history.html.j2").render()
    assert "MMXReleaseVisualHistory" in markup
    assert 'data-rrh-chart' in markup
    assert 'role="status"' in markup


def test_first_print_receipts_require_integrity_first_sequence_and_unique_truth(tmp_path,monkeypatch):
    """Synthetic observations are test fixtures only, never chart seed data."""
    def row(period,actual,receipt,*,sequence="first",integrity="ok",observed="2026-10-15T12:33:00Z"):
        return {"release":"ppi_finaldemand","period":period,"unit":"percent",
                "row_type":"actual","sequence":sequence,"actual":actual,
                "receipt_id":receipt,"integrity":integrity,"observed_at":observed,
                "source_released_at":"2026-10-15T12:30:00Z",
                "source_url":"https://www.bls.gov/news.release/ppi.htm"}
    entries=[
        row("2026-08",0.3,"legit"),
        row("2026-08",0.3,"legit"),             # exact duplicate idempotent
        row("2026-08",99,"bad",integrity="bad"),  # defective input rejected
        row("2026-09",0.2,"first"),
        row("2026-09",0.4,"conflict"),            # conflicting first prints withheld
        row("2026-10",0.5,"future",observed="2026-11-14T12:33:00Z"),
        row("2026-08",0.9,"revised",sequence="correction_candidate"),
    ]
    monkeypatch.setattr(visual,"load_actual_ledger",lambda path:entries)
    checked=[]
    def integrity(receipt, *, defects_path):
        checked.append(receipt["receipt_id"])
        return [] if receipt["integrity"]=="ok" else ["source_bad"]
    monkeypatch.setattr(visual,"receipt_integrity_errors",integrity)
    events=visual._receipt_groups(tmp_path,visual._clock(NOW))
    assert [e["period"] for e in events["ppi_finaldemand"]]==["2026-08"]
    assert events["ppi_finaldemand"][0]["value"]==0.3
    assert events["ppi_finaldemand"][0]["basis"]=="verified_official_first_print_mom"
    assert "bad" in checked and "future" not in checked


def test_visual_javascript_syntax_in_node_when_available():
    import shutil
    import subprocess
    if not shutil.which("node"):
        pytest.skip("Node unavailable in this CI image")
    script=ROOT/"templates/release_visual_history.js"
    result=subprocess.run(["node","--check",str(script)],capture_output=True,text=True,timeout=10)
    assert result.returncode==0, result.stderr


def test_bls_annual_headline_is_unadjusted_but_monthly_is_adjusted(tmp_path, monkeypatch):
    """BLS PPI/CPI YoY must never silently use the SA index after NSA exists."""
    _manifest(tmp_path,collected="2026-10-16T18:00:00Z")
    nsa = tmp_path/"data/fred_vintage/release_targets/PPIFID_all_vintages.parquet"
    nsa.write_bytes(b"nsa-fixture")
    manifest = tmp_path/"data/fred_vintage/release_targets/manifest.json"
    payload=json.loads(manifest.read_text())
    payload["series"]["PPIFID"]={"path":"data/fred_vintage/release_targets/PPIFID_all_vintages.parquet",
        "status":"written","artifact_bytes":len(b"nsa-fixture"),
        "artifact_sha256":sha256(b"nsa-fixture").hexdigest()}
    manifest.write_text(json.dumps(payload))
    seen=[]
    def loader(path, *, series_id):
        seen.append(series_id)
        frame=_frame()
        if series_id=="PPIFID":
            frame=frame.copy()
            frame.loc[frame["value"]<200,"value"]=frame.loc[frame["value"]<200,"value"]*1.1
            # Annual raw growth remains valid, but at 2026-07 first-year
            # growth differs from the seasonally adjusted mock series.
            frame.loc[frame["period"]>=pd.Timestamp("2026-01-01"),"value"] += 6
        return frame
    monkeypatch.setattr(visual,"load_full_vintage_parquets",loader)
    result=visual.build_release_visual_history(tmp_path,asof=NOW)
    ppi=next(x for x in result["series"] if x["release"]=="ppi_finaldemand")
    assert ppi["basis_metadata"]["yoy"] == {
        "series_id":"PPIFID","seasonal_adjustment":"NSA",
        "official_reported_basis_comparable":True,"first_print":False,
        "basis_note":"NSA_index_derived_yoy_not_official_first_print",
    }
    assert ppi["basis_metadata"]["mom"]["series_id"]=="PPIFIS"
    assert ppi["basis_metadata"]["mom"]["seasonal_adjustment"]=="SA"
    assert ppi["yoy"] != visual._frame_points(_frame(),date(2026,10,16))["yoy"]
    assert ppi["mom"] == visual._frame_points(_frame(),date(2026,10,16))["mom"]
    assert set(seen)=={"PPIFIS","PPIFID"}


def test_missing_optional_nsa_is_explicitly_sa_proxy(tmp_path,monkeypatch):
    _manifest(tmp_path,collected="2026-10-16T18:00:00Z")
    monkeypatch.setattr(visual,"load_full_vintage_parquets",lambda *a,**k:_frame())
    result=visual.build_release_visual_history(tmp_path,asof=NOW)
    ppi=next(x for x in result["series"] if x["release"]=="ppi_finaldemand")
    assert ppi["status"]=="available"
    assert ppi["basis_metadata"]["yoy"]["seasonal_adjustment"]=="SA"
    assert not ppi["basis_metadata"]["yoy"]["official_reported_basis_comparable"]
    assert "ppi_finaldemand:nsa:official_nsa_series_not_collected" in result["reason_codes"]
    assert ppi["basis_metadata"]["mom"]["official_reported_basis_comparable"] is True


def test_bls_october_2026_cpi_yoy_gap_not_filled():
    levels={f"2025-{i:02d}":100.0 for i in range(1,13) if i!=10}
    levels.update({"2026-09":105.2,"2026-10":106.1})
    yearly=visual._change(levels,12)
    assert "2026-10" not in [p["period"] for p in yearly]
    assert "2026-09" in [p["period"] for p in yearly]


def test_visual_only_nsa_series_not_admitted_to_forecast_scoring():
    from engine.release_target_truth import (CHART_ONLY_INDEX_SERIES,
        SUPPORTED_SERIES, VINTAGE_STORE_SERIES, ReleaseTargetTruthError,
        reconstruct_release_target)
    for sid in ("PPIFID","CPIAUCNS","CPILFENS"):
        assert sid in CHART_ONLY_INDEX_SERIES
        assert sid in VINTAGE_STORE_SERIES
        assert sid not in SUPPORTED_SERIES
        with pytest.raises(ReleaseTargetTruthError,match="chart_only_index_must_not_be_reconstructed"):
            reconstruct_release_target(pd.DataFrame(),series_id=sid,period="2026-10")


def test_missing_optional_nsa_cannot_veto_core_vintage_publication(tmp_path):
    from scripts.collect_release_target_vintages import collect_release_target_vintages
    def provider(**kwargs):
        if kwargs["series_id"]=="PPIFID":
            raise RuntimeError("synthetic unavailable optional NSA source")
        return pd.DataFrame([
            {"period":"2026-07-01", "realtime_start":"2026-08-12",
             "realtime_end":"9999-12-31","value":100.0},
            {"period":"2026-08-01", "realtime_start":"2026-09-11",
             "realtime_end":"9999-12-31","value":100.3},
        ])
    result=collect_release_target_vintages(
        repo_root=tmp_path,series_ids=["CPIAUCSL","PPIFID"],
        api_key="test",fetcher=provider)
    assert result["status"]=="ok"
    assert result["optional_series_status"]=="partial"
    assert result["optional_series_failures"]==["PPIFID"]
    manifest=json.loads((tmp_path/"data/fred_vintage/release_targets/manifest.json").read_text())
    assert manifest["status"]=="ok"
    assert manifest["series"]["CPIAUCSL"]["status"]=="written"
    assert manifest["series"]["PPIFID"]["status"]=="failed"
    assert (tmp_path/"data/fred_vintage/release_targets/CPIAUCSL_all_vintages.parquet").is_file()
    assert not (tmp_path/"data/fred_vintage/release_targets/PPIFID_all_vintages.parquet").exists()


def test_missing_core_vintage_still_aborts_optional_publication(tmp_path):
    from scripts.collect_release_target_vintages import collect_release_target_vintages
    def provider(**kwargs):
        if kwargs["series_id"]=="CPIAUCSL":
            raise RuntimeError("synthetic failed core source")
        return pd.DataFrame([
            {"period":"2026-08-01","realtime_start":"2026-09-11",
             "realtime_end":"9999-12-31","value":100.3},
        ])
    result=collect_release_target_vintages(
        repo_root=tmp_path,series_ids=["CPIAUCSL","PPIFID"],
        api_key="test",fetcher=provider)
    assert result["status"]=="partial"
    assert result["publication_status"]=="aborted_before_source_mutation"
    assert not (tmp_path/"data/fred_vintage/release_targets/manifest.json").exists()
    assert not (tmp_path/"data/fred_vintage/release_targets/PPIFID_all_vintages.parquet").exists()


def test_ui_always_discloses_sa_proxy_and_official_nsa_basis():
    script=(ROOT/"templates/release_visual_history.js").read_text()
    partial=(ROOT/"templates/_release_visual_history.html.j2").read_text()
    for expected in ("SA-index YoY proxy","BLS official NSA","sourceBasis.series_id",
                     "official_reported_basis_comparable"):
        assert expected in script
    assert "BLS CPI/PPI" in partial and "October 2025 CPI" in partial


@pytest.mark.parametrize("release", tuple(visual.TARGETS))
@pytest.mark.parametrize("basis,lag", [("mom", 1), ("yoy", 12)])
@pytest.mark.parametrize("previous,current", [(1e-308, 1e308), (1.0, 1e307)])
def test_finite_inputs_cannot_publish_nonfinite_rates(
    tmp_path, monkeypatch, release, basis, lag, previous, current
):
    """Real sealed Parquets/manifest/builder; only the provider and clock are synthetic."""
    import requests
    from scripts import collect_release_target_vintages as collector

    def no_network(*args, **kwargs):
        raise AssertionError("unexpected provider request in offline source qualification")

    monkeypatch.setattr(requests.Session, "request", no_network)
    monkeypatch.setattr(collector, "_utc_now", lambda: "2026-11-13T14:00:00+00:00")
    series_id = (visual.YOY_HEADLINE_SERIES[release] if basis == "yoy"
                 else visual.TARGETS[release][0])
    end = 2026 * 12 + 9  # October 2026, before the fixed collection clock.

    def provider(**kwargs):
        rows = []
        for month in range(end - 33, end + 1):
            value = 100.0 + (month - (end - 33)) / 10.0
            if kwargs["series_id"] == series_id:
                if month == end - lag:
                    value = previous
                elif month == end:
                    value = current
            rows.append({"period": f"{month // 12:04d}-{month % 12 + 1:02d}-01",
                         "realtime_start": "2026-11-01", "realtime_end": "9999-12-31",
                         "value": value})
        return pd.DataFrame(rows)

    receipt = collector.collect_release_target_vintages(
        repo_root=tmp_path, api_key="synthetic-test-key", fetcher=provider)
    assert receipt["status"] == "ok"
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = visual.build_release_visual_history(tmp_path, asof=NOW)
    json.dumps({"release_visual_history": result}, allow_nan=False)
    assert {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
    row = next(item for item in result["series"] if item["release"] == release)
    assert "2026-10" not in {p["period"] for p in row[basis]}
    assert "2026-08" in {p["period"] for p in row[basis]}
    assert "2026-10" in row["withheld_periods"][basis]
    assert row["status"] == "partial" and result["status"] == "partial"
    assert f"{release}:{basis}:derived_rate_nonfinite" in result["reason_codes"]
    assert all(item["status"] == "available" for item in result["series"] if item is not row)
    assert result["display_only"] is True and not any(result["authority"].values())


def test_all_unrepresentable_rates_remain_unavailable():
    levels = {"2025-01": 1e-308, "2026-01": 1e308}
    assert visual._change(levels, 12) == []


# Executes the complete committed controller and the actual parent refresh function.
# DOM, response and clock are synthetic; this is not browser/visual acceptance.
_NATIVE_VISUAL_PROBE = r"""
const fs=require('fs'), path=require('path'), vm=require('vm'), assert=require('assert/strict');
const root=process.argv[1], scenario=process.argv[2], span=Number(process.argv[3]);
class Element {
  constructor(tag) { this.tagName=tag; this.children=[]; this.attrs={}; this.dataset={}; this.events={}; this.value=''; this.text=''; }
  set textContent(value) { this.text=String(value); this.children=[]; }
  get textContent() { return this.text+this.children.map(n=>n.textContent).join(''); }
  appendChild(node) { this.children.push(node); return node; }
  setAttribute(key,value) { this.attrs[key]=String(value); }
  getAttribute(key) { return this.attrs[key]||null; }
  addEventListener(name,fn) { (this.events[name] ||= []).push(fn); }
  dispatchEvent(event) { (this.events[event.type]||[]).forEach(fn=>fn(event)); }
  querySelector(selector) {
    const option=selector.match(/^option\[value="([^"]+)"\]$/);
    return option ? (this.options||{})[option[1]]||null : (this.roles||{})[selector]||null;
  }
}
const host=new Element('section'); host.roles={};
for(const role of ['target','basis','window','state','value','delta','interpretation','meta','chart','facts','table','chart-title','source'])
  host.roles['[data-rrh-'+role+']']=new Element(role==='chart'?'svg':'div');
function role(name) { return host.roles['[data-rrh-'+name+']']; }
for(const [name,values] of [['target',['ppi_finaldemand','cpi_headline','cpi_core','pce_headline','pce_core']],['basis',['yoy','mom']],['window',['12','36','60']]]) {
  role(name).options={}; for(const value of values) role(name).options[value]=new Element('option');
}
const docEvents={};
const document={hidden:false, documentElement:new Element('html'),
  createElement:tag=>new Element(tag), createElementNS:(_ns,tag)=>new Element(tag),
  getElementById:id=>id==='rr-visual-history'?host:null,
  addEventListener:(name,fn)=>(docEvents[name] ||= []).push(fn),
  dispatchEvent:event=>(docEvents[event.type]||[]).forEach(fn=>fn(event))};
document.documentElement.setAttribute('lang','en');
let clock=Date.parse('2026-11-13T15:00:00Z'), fetches=0, failed=false, radarRenders=0;
class ClockDate extends Date { constructor(...args) { super(...(args.length?args:[clock])); } static now() { return clock; } }
const window={};
const denied={can_score:false,can_rank:false,can_gate:false,can_size:false,can_trade:false};
function fixture(points) {
  return {schema:'release_visual_history.v1', display_only:true, authority:denied, status:'available',
    asof:'2026-11-13T15:00:00Z',source_collected_at:'2026-11-13T14:00:00Z',source_status:'recent',
    series:['ppi_finaldemand','cpi_headline','cpi_core','pce_headline','pce_core'].map(release=>({
      release,status:'available',yoy:points,mom:points,first_prints:[],
      basis_metadata:{yoy:{series_id:'PPIFID',seasonal_adjustment:'NSA',official_reported_basis_comparable:true},
                      mom:{series_id:'PPIFIS',seasonal_adjustment:'SA',official_reported_basis_comparable:true}}}))};
}
let payload={upcoming:[],asof:'2026-11-13T15:00:00Z',release_visual_history:fixture([
  {period:'2026-08',value:2.1},{period:'2026-09',value:2.2},{period:'2026-10',value:2.3}])};
const context=vm.createContext({window,document,Date:ClockDate,console,
  setTimeout:()=>1,clearTimeout:()=>{},AbortController,
  fetch:()=>{fetches++;return failed?Promise.reject(new Error('offline fixture')):
    Promise.resolve({ok:true,json:()=>Promise.resolve(payload)});},
  _rrForecastAsOf:'',_rrForecastFailed:false,_rrUpdateCountdowns:()=>{},_rrUpdateSnapshotNotice:()=>{},
  renderRadar:data=>{radarRenders++;window.MMXReleaseVisualHistory.render(host,data&&data.release_visual_history,data&&data.release_surprise_confirmation);}});
vm.runInContext(fs.readFileSync(path.join(root,'templates/release_visual_history.js'),'utf8'),context);
function render(history) { window.MMXReleaseVisualHistory.render(host,history,null); }
function change(name,value) { role(name).value=String(value);role(name).dispatchEvent({type:'change'}); }
function plotted() { return role('chart').children.filter(n=>n.tagName==='circle'&&n.children[0]?.tagName==='title').map(n=>n.children[0].textContent.slice(0,7)); }
function finiteSvg() { for(const node of role('chart').children) for(const value of Object.values(node.attrs)) assert(!/NaN|Infinity/.test(value),value); }
async function main() {
  if(scenario==='window') {
    const end=2029*12+11, rows=[];
    for(let month=end-71;month<=end;month++) if(month!==end-2)
      rows.push({period:String(Math.floor(month/12))+'-'+String(month%12+1).padStart(2,'0'),value:1+(month-(end-71))/100});
    const history=fixture(rows);history.asof='2030-01-02T15:00:00Z';history.source_collected_at=history.asof;
    clock=Date.parse(history.asof);render(history);change('window',span);
    const observed=plotted(), start=end-span+1;
    assert.equal(observed[0],String(Math.floor(start/12))+'-'+String(start%12+1).padStart(2,'0'));
    assert.equal(observed.length,span-1);assert(!observed.includes('2029-10'));
    assert.equal(role('chart').children.filter(n=>n.tagName==='path'&&n.attrs.fill==='none').length,2);
    finiteSvg();
  } else if(scenario==='language') {
    render(payload.release_visual_history);render(payload.release_visual_history);
    change('target','cpi_core');change('basis','mom');change('window',12);
    document.documentElement.setAttribute('data-lang','zh');document.documentElement.setAttribute('lang','zh');
    document.dispatchEvent({type:'langchange'});
    assert.equal(role('target').options.cpi_core.textContent,'核心 CPI');
    assert.equal(role('basis').options.mom.textContent,'环比');assert.equal(role('window').options['12'].textContent,'1 年');
    assert.equal(role('target').value,'cpi_core');assert.equal(role('basis').value,'mom');assert.equal(role('window').value,'12');
    assert.equal(docEvents.langchange.length,1);assert.equal(fetches,0);
    render(null);document.documentElement.setAttribute('lang','en');document.documentElement.setAttribute('data-lang','en');
    document.dispatchEvent({type:'langchange'});assert.equal(role('target').options.cpi_core.textContent,'Core CPI');
  } else if(scenario==='refresh_same'||scenario==='refresh_error') {
    const dashboard=fs.readFileSync(path.join(root,'templates/dashboard.html.j2'),'utf8');
    const start=dashboard.indexOf('    var _rrForecastSignature = null;');
    const end=dashboard.indexOf('    _rrRefreshForecast();',start);
    assert(start>=0&&end>start);vm.runInContext(dashboard.slice(start,end),context);
    context._rrRefreshForecast();await new Promise(resolve=>setImmediate(resolve));
    assert(role('state').textContent.includes('Historical series available.'));assert.equal(radarRenders,1);
    clock+=73*3600000;failed=scenario==='refresh_error';
    context._rrRefreshForecast();await new Promise(resolve=>setImmediate(resolve));
    assert(role('state').textContent.includes('Archived history — not a current release.'));
    assert.equal(radarRenders,1);assert.equal(fetches,2);assert.deepEqual(plotted(),['2026-08','2026-09','2026-10']);
    document.hidden=true;context._rrRefreshForecast();assert.equal(fetches,2);
  } else if(scenario==='partial') {
    const history=payload.release_visual_history;history.status='partial';history.series[0].status='partial';
    history.series[0].withheld_periods={yoy:['2026-09'],mom:[]};history.series[0].yoy=history.series[0].yoy.filter(p=>p.period!=='2026-09');
    render(history);assert.deepEqual(plotted(),['2026-08','2026-10']);
    assert(role('state').textContent.includes('Some historical rates are unavailable'));
    assert(role('state').textContent.includes('部分历史变化率不可用'));
    assert(role('delta').textContent.includes('Monthly change unavailable.'));finiteSvg();
  } else if(scenario==='empty_basis') {
    const history=payload.release_visual_history;history.status='partial';history.series[0].status='partial';
    history.series[0].withheld_periods={yoy:['2026-10'],mom:[]};history.series[0].yoy=[];
    render(history);assert.equal(plotted().length,0);assert(role('state').textContent.includes('Historical series unavailable.'));
    change('basis','mom');assert.equal(plotted().length,3);assert(role('state').textContent.includes('Historical series partially available.'));
  } else if(scenario==='controls') {
    const one=fixture([{period:'2026-10',value:2.3}]);render(one);assert.deepEqual(plotted(),['2026-10']);finiteSvg();
    render({...one,asof:'2026-11-14T15:00:00Z'});assert.equal(plotted().length,0);
    const duplicate=fixture([{period:'2026-10',value:2.3},{period:'2026-10',value:2.4}]);render(duplicate);assert.equal(plotted().length,0);
    assert(role('state').textContent.includes('Historical series unavailable.'));
    render(fixture([{period:'2026-10',value:501}]));assert.equal(plotted().length,0);
    assert(role('state').textContent.includes('Historical series unavailable.'));
    render({...one,authority:{...denied,can_trade:true}});assert.equal(plotted().length,0);assert.equal(fetches,0);
  } else throw new Error('unknown scenario');
  console.log(JSON.stringify({scenario,span,fetches,radarRenders,status:'passed'}));
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});
"""


def _native_visual_case(scenario, window=0):
    import shutil
    import subprocess
    if not shutil.which("node"):
        pytest.skip("Node unavailable in this CI image")
    run = subprocess.run(["node", "-e", _NATIVE_VISUAL_PROBE, str(ROOT), scenario, str(window)],
                         capture_output=True, text=True, timeout=15)
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(run.stdout)["status"] == "passed"


@pytest.mark.parametrize("window", [12, 36, 60])
def test_native_calendar_windows_preserve_missing_months(window):
    _native_visual_case("window", window)


@pytest.mark.parametrize("scenario", ["language", "refresh_same", "refresh_error", "partial", "empty_basis", "controls"])
def test_native_visual_lifecycle_and_data_controls(scenario):
    _native_visual_case(scenario)
