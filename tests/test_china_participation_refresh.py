"""Late inputs repair the current view without rewriting first-observed evidence."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

from engine import china_participation as participation
from scripts import build_china_participation as producer
from scripts import build_china_altdata as page


def frame():
    dates = pd.date_range("2026-10-20", periods=4)
    return pd.DataFrame({
        "turnover_z20":[-1.03,-.8,-.6,np.nan],
        "margin_chg_5d":[-2.57,-2.1,-1.9,np.nan],
        "qvix_z":[.1,.2,.54,np.nan], "zt_breadth":[.5,.4,.26,.75],
        "regime":["dormant"]*4, "who_controls":["mixed"]*4, "risk":["low"]*4,
        "backfill":[False]*4, "evidence":[""]*4,"contradictions":["[]"]*4,"data_gaps":[""]*4,
    },index=dates)


def test_delayed_same_date_arrival_refreshes_projection_not_archive(tmp_path, monkeypatch):
    current = frame()
    archive = current.copy(deep=True)
    archive.loc["2026-10-21":,["turnover_z20","margin_chg_5d"]]=np.nan
    archive_path=tmp_path/"tape.parquet";archive.to_parquet(archive_path)
    original=archive_path.read_bytes()
    monkeypatch.setattr(producer,"_TAPE_PATH",archive_path)
    monkeypatch.setattr(producer,"_JSON_PATH",tmp_path/"legacy.json")
    monkeypatch.setattr(producer,"_CURRENT_JSON_PATH",tmp_path/"current.json")
    monkeypatch.setattr(producer,"_sanity_print",lambda _:None)
    calls=[]
    def build(**kwargs):
        calls.append(kwargs)
        return current.copy(deep=True)
    monkeypatch.setattr(participation,"build_tape",build)
    assert producer.main()==0
    assert len(calls)==1
    assert archive_path.read_bytes()==original
    assert json.loads((tmp_path/"legacy.json").read_text())["date"]=="2026-10-20"
    snap=json.loads((tmp_path/"current.json").read_text())
    assert snap["date"]=="2026-10-22" and snap["latest_date"]=="2026-10-23"
    assert snap["previous_observation"]["date"]=="2026-10-21"
    assert snap["previous_observation"]["turnover_z20"]==-.8
    assert snap["schema"]=="china_participation.current.v1"
    assert snap["projection_kind"]=="current_source_recomputation"
    assert "backfill" not in snap and snap["source_available_at"] is None
    assert "not_point_in_time" in snap["history_qualification"]


def test_nonnull_correction_and_rolling_changes_do_not_restate_archive():
    original=frame();current=frame()
    current.loc["2026-10-22","margin_chg_5d"]=-.2
    assert_frame_equal(producer._append_new_rows(original,current),original)
    assert participation.current_projection(current)["margin_chg_5d"]==-.2
    series=pd.Series(np.arange(30,dtype=float)+10,index=pd.date_range("2026-09-01",periods=30))
    corrected=series.copy();corrected.iloc[-5]=200
    old_z=participation._zscore(series,20,10);new_z=participation._zscore(corrected,20,10)
    assert old_z.iloc[-1]!=new_z.iloc[-1]
    assert original.loc["2026-10-22","margin_chg_5d"]==-1.9


def test_append_is_idempotent_and_existing_rows_win():
    old=frame().iloc[:2].copy();recomputed=frame()
    recomputed.iloc[0,recomputed.columns.get_loc("turnover_z20")]=9
    merged=producer._append_new_rows(old,recomputed)
    assert_frame_equal(merged.iloc[:2],old)
    assert len(merged)==4
    assert_frame_equal(producer._append_new_rows(merged,recomputed),merged)
    assert not merged["backfill"].any()


def test_explicit_date_column_and_datetime_index_align_identically():
    rows=pd.DataFrame({"date":["2026-10-21","bad","2026-10-22"],
                       "limit_up_breadth_pct":[.4,999,.26],"universe_n":[1876,0,1875]})
    normalized=participation._dated_limit_tape(rows)
    indexed=rows.iloc[[0,2]].set_index("date")
    indexed.index=pd.to_datetime(indexed.index)
    assert_series_equal(normalized["limit_up_breadth_pct"],
                        participation._dated_limit_tape(indexed)["limit_up_breadth_pct"])
    assert normalized.index.min().year==2026
    assert participation._dated_limit_tape(pd.DataFrame({"limit_up_breadth_pct":[.4]})).empty


def test_limit_loader_uses_date_column_not_row_numbers(tmp_path, monkeypatch):
    path=tmp_path/"limit_tape.parquet"
    pd.DataFrame({"date":["2026-10-22","2026-10-23"],"limit_up_breadth_pct":[.2667,.7487],
                  "universe_n":[1875,1870],"failed_up_seal_count":[3,0],"limit_up_count":[5,14]}).to_parquet(path,index=False)
    monkeypatch.setattr(participation,"_data_path",lambda *parts:str(path) if parts[0]=="china_microstructure" else str(tmp_path/"absent"))
    series,gaps=participation._load_limit_breadth()
    assert series.loc[pd.Timestamp("2026-10-23")]==.7487 and not gaps
    # Run the real frame alignment/classification with synthetic independent inputs.
    idx=series.index
    monkeypatch.setattr(participation,"_load_turnover",lambda:(pd.Series([100.,120.],index=idx),[]))
    monkeypatch.setattr(participation,"_load_margin",lambda:(pd.DataFrame({"margin_balance":[10.,11.],"margin_chg_5d":[0.,1.],"margin_to_mcap":[2.,2.]},index=idx),[]))
    for name in ("_load_southbound","_load_etf_flows","_load_qvix","_load_broker_rs"):
        monkeypatch.setattr(participation,name,lambda:(pd.Series(dtype=float),[]))
    tape=participation.build_tape()
    assert tape.loc[idx[0],"failed_seal_ratio"]==.6
    assert tape.loc[idx[1],"zt_universe_n"]==1870
    assert tape.loc[idx[1],"failed_seal_ratio"]==0


def test_first_render_recomputes_only_generated_site_output(tmp_path, monkeypatch):
    legacy=tmp_path/"chinastatedata"/"participation.json";legacy.parent.mkdir()
    legacy.write_text('{"date":"2026-10-20","regime":"dormant"}')
    before=legacy.read_bytes()
    monkeypatch.setattr(participation,"build_tape",lambda **_:frame())
    monkeypatch.setattr(producer,"_write_tape",lambda _:(_ for _ in ()).throw(AssertionError("archive write")))
    snap=page._current_participation(tmp_path)
    assert snap["date"]=="2026-10-22"
    assert legacy.read_bytes()==before
    assert (legacy.parent/"participation_current.json").exists()


def test_source_failure_has_explicit_archival_fallback(tmp_path, monkeypatch):
    legacy=tmp_path/"chinastatedata"/"participation.json";legacy.parent.mkdir()
    legacy.write_text('{"date":"2026-10-20","regime":"dormant"}')
    def fail(**_): raise OSError("fixture source missing")
    monkeypatch.setattr(participation,"build_tape",fail)
    snap=page._current_participation(tmp_path)
    assert snap["date"]=="2026-10-20"
    assert snap["projection_kind"]=="first_observed_archive"
    assert snap["computed_at"] is None


def test_margin_change_keeps_missing_current_and_lagged_balance_unavailable(tmp_path, monkeypatch):
    path = tmp_path / "balance.parquet"
    balances = pd.Series(np.arange(12, dtype=float) + 100, index=pd.date_range("2026-10-01", periods=12))
    balances.iloc[1] = np.nan
    balances.iloc[-1] = np.nan
    pd.DataFrame({"margin_total": balances}).to_parquet(path)
    monkeypatch.setattr(participation, "_data_path", lambda *parts: str(path))
    readings, _ = participation._load_margin()
    assert pd.isna(readings["margin_chg_5d"].iloc[6])
    assert pd.isna(readings["margin_chg_5d"].iloc[-1])
    assert pd.notna(readings["margin_chg_5d"].iloc[-2])


def test_broker_strength_requires_both_current_return_endpoints(tmp_path, monkeypatch):
    broker_path, csi_path = tmp_path / "broker.parquet", tmp_path / "csi.parquet"
    monkeypatch.setattr(participation, "_data_path", lambda *parts:
                        str(broker_path if parts[0] == "china_sectors" else csi_path))
    dates = pd.date_range("2026-09-01", periods=30)
    for missing in ("broker", "csi"):
        broker = pd.Series(np.exp(np.arange(30) * .01), index=dates)
        csi = pd.Series(np.exp(np.arange(30) * .005), index=dates)
        (broker if missing == "broker" else csi).iloc[-1] = np.nan
        pd.DataFrame({"close": broker}).to_parquet(broker_path)
        pd.DataFrame({"close": csi}).to_parquet(csi_path)
        readings, _ = participation._load_broker_rs()
        assert pd.notna(readings.iloc[-2])
        assert pd.isna(readings.iloc[-1]), missing
