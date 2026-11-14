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
    _manifest(tmp_path)
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
    _manifest(tmp_path)
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
