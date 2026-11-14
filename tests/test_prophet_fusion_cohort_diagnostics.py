"""Synthetic contracts only: no held-out market outcomes or live store writes."""
from __future__ import annotations

from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd
import pytest

from engine.entry_radar.entry_events import EntryEvent, SourceIdentity
from engine.vol_regime import _pctile
from lib.nyse_calendar import sessions_between
from scripts import prophet_fusion_cohort_diagnostics as d
from scripts.prophet_fusion_mechanisms import canonical_outcome


@pytest.fixture
def prices():
    grid = pd.DatetimeIndex(sessions_between(date(2016, 1, 4), date(2019, 12, 31)))
    n = len(grid)
    return grid, pd.Series(np.linspace(12, 35, n), index=grid), pd.Series(np.linspace(80, 140, n), index=grid)


def event(day, *, known=True, final=False, ticker="FIX"):
    return EntryEvent(producer="synthetic-fixture", ticker=ticker, family="grey_dot",
        signal_ts=str(day.date()), signal_known_ts=str(day.date()) if known else None,
        source_identity=SourceIdentity(source_hash="fixture", signal_era="synthetic", detector_spec_hash="fixture"),
        field_origin={"signal_known_ts": "emitter_verbatim" if known else "artifact_absent"},
        bar_state="confirmed" if final else "provisional", final=final,
        finality_basis="synthetic_fixture", detector_id="G0_GREY_DOT@1")


def test_trajectory_uses_exact_native_rank_and_lags_one_session(prices):
    grid, vix, vvix = prices
    out = d.implied_volatility_trajectory(vix, vvix, grid)
    i = 400
    assert out.iloc[i].vix_level == vix.iloc[i-1]
    assert out.iloc[i].feature_session == grid[i-1]
    ma = vix.rolling(20).mean()
    assert out.iloc[i].vix_ma20_slope5 == pytest.approx(ma.iloc[i-1]/ma.iloc[i-6]-1)
    assert out.iloc[i].vix_rank252 == _pctile(vix, 252).iloc[i-1]
    assert out.iloc[251].rank_pair_available == False
    assert out.iloc[252].rank_pair_available == True
    assert out.iloc[i].direction_pair == "BOTH_RISING"
    assert out.attrs["promotion_eligible"] is False


def test_future_suffix_and_same_day_close_cannot_change_current_context(prices):
    grid, vix, vvix = prices
    prefix = d.implied_volatility_trajectory(vix.iloc[:401], vvix.iloc[:401], grid[:401])
    changed_vix, changed_vvix = vix.copy(), vvix.copy()
    changed_vix.iloc[400:] *= 8
    changed_vvix.iloc[400:] *= 3
    full = d.implied_volatility_trajectory(changed_vix, changed_vvix, grid)
    pd.testing.assert_frame_equal(prefix, full.iloc[:401])


@pytest.mark.parametrize("a,b,expected", [(1,1,"BOTH_RISING"),(-1,-1,"BOTH_FALLING"),
    (1,-1,"VIX_RISING_VVIX_FALLING"),(-1,1,"VIX_FALLING_VVIX_RISING"),
    (0,0,"FLAT_OR_MIXED"),(0,1,"FLAT_OR_MIXED")])
def test_direction_labels_are_measurements_not_risk_verdicts(prices,a,b,expected):
    grid, _, _ = prices
    x=pd.Series(100+np.linspace(0,20,len(grid))*a,index=grid)
    y=pd.Series(100+np.linspace(0,20,len(grid))*b,index=grid)
    out=d.implied_volatility_trajectory(x,y,grid)
    assert out.iloc[-1].direction_pair==expected
    assert not any(c in out.columns for c in ("risk_score","buy","size","forecast_probability"))


def test_missing_session_is_not_filled_or_compressed(prices):
    grid,vix,vvix=prices
    out=d.implied_volatility_trajectory(vix,vvix.drop(grid[400]),grid)
    assert pd.isna(out.loc[grid[401],"vvix_level"])
    assert not out.loc[grid[401],"trajectory_available"]
    assert not out.loc[grid[420],"trajectory_available"]
    assert not out.loc[grid[650],"rank_pair_available"]
    assert out.loc[grid[653],"rank_pair_available"]


@pytest.mark.parametrize("bad",[0,-1,np.inf,-np.inf,"bad"])
def test_invalid_levels_refuse(prices,bad):
    grid,vix,vvix=prices
    x=vix.astype(object);x.iloc[15]=bad
    with pytest.raises(d.DiagnosticRefusal):d.implied_volatility_trajectory(x,vvix,grid)


def test_boolean_level_refuses(prices):
    grid,_,vvix=prices
    with pytest.raises(d.DiagnosticRefusal):d.implied_volatility_trajectory(pd.Series(True,index=grid),vvix,grid)


@pytest.mark.parametrize("fault",["duplicate","reversed","non_session","tz","hole","intraday"])
def test_calendar_and_identity_faults_refuse(prices,fault):
    grid,vix,vvix=prices
    if fault=="duplicate":g=grid.insert(2,grid[2])
    elif fault=="reversed":g=grid[::-1]
    elif fault=="non_session":g=grid.insert(0,pd.Timestamp("2016-01-03"))
    elif fault=="tz":g=grid.tz_localize("UTC")
    elif fault=="hole":g=grid.delete(300)
    else:g=grid+pd.Timedelta(hours=12)
    with pytest.raises(d.DiagnosticRefusal):d.implied_volatility_trajectory(vix,vvix,g)


def test_definition_is_not_a_grid():
    with pytest.raises(d.DiagnosticRefusal):d.TrajectorySpec(moving_average_sessions=19)


def test_native_event_consumer_preserves_clock_missingness_and_finality(prices):
    grid,vix,vvix=prices;ctx=d.implied_volatility_trajectory(vix,vvix,grid)
    native=[event(grid[400]),event(grid[401],known=False),event(grid[402],final=True)]
    originals=[x.to_dict() for x in native]
    rows=d.join_native_event_context(native,ctx)
    assert [r["event_id"] for r in rows]==[x.event_id for x in native]
    assert rows[0]["join_status"]=="JOINED_DATE_PROXY_ONLY"
    assert rows[0]["bar_state"]=="provisional" and rows[0]["final"] is False
    assert rows[0]["context"]["feature_session"]==grid[399]
    assert rows[1]["join_status"]=="SIGNAL_KNOWABILITY_UNAVAILABLE" and rows[1]["context"] is None
    assert rows[2]["final"] is True
    assert [x.to_dict() for x in native]==originals
    assert all(r["promotion_eligible"] is False for r in rows)


def test_unknown_clock_never_uses_chart_label(prices):
    grid,vix,vvix=prices;ctx=d.implied_volatility_trajectory(vix,vvix,grid)
    a=event(grid[400],known=False)
    row=d.join_native_event_context([a],ctx)[0]
    assert row["context"] is None and row["signal_ts"]==str(grid[400].date())


@pytest.mark.parametrize("known",["garbage","2018-11-03","2018-11-05T16:00:00Z","2010-01-04"])
def test_invalid_known_clock_is_retained_as_unavailable(prices,known):
    grid,vix,vvix=prices;ctx=d.implied_volatility_trajectory(vix,vvix,grid)
    a=replace(event(pd.Timestamp("2018-11-01")),signal_known_ts=known)
    row=d.join_native_event_context([a],ctx)[0]
    assert row["join_status"]=="INVALID_KNOWN_SESSION" and row["context"] is None


def test_duplicate_native_event_and_fake_schema_refuse(prices):
    grid,vix,vvix=prices;ctx=d.implied_volatility_trajectory(vix,vvix,grid);a=event(grid[400])
    with pytest.raises(d.DiagnosticRefusal):d.join_native_event_context([a,a],ctx)
    with pytest.raises(d.DiagnosticRefusal):d.join_native_event_context([a.to_dict()],ctx)
    ctx.attrs["promotion_eligible"]=True
    with pytest.raises(d.DiagnosticRefusal):d.join_native_event_context([a],ctx)


def test_join_rejects_same_session_context_laundering(prices):
    grid,vix,vvix=prices;ctx=d.implied_volatility_trajectory(vix,vvix,grid)
    ctx.loc[grid[400],"feature_session"]=grid[400]
    with pytest.raises(d.DiagnosticRefusal):d.join_native_event_context([event(grid[400])],ctx)


CONTRACT={"outcome_definition":"fixture_no_undercut_v1","horizon":"21","weighting":"equal_episode","population_rule":"fixture_dated_members"}


def decompose(a,b,**kw):
    return d.rate_change_decomposition(a,b,before_contract=CONTRACT,after_contract=kw.get("contract",CONTRACT))


def test_apparent_success_lift_can_be_entirely_market_state_mix():
    a={"calm":{"weight":.8,"rate":.4},"repair":{"weight":.2,"rate":.8}}
    b={"calm":{"weight":.2,"rate":.4},"repair":{"weight":.8,"rate":.8}}
    r=decompose(a,b)
    assert r["difference"]==pytest.approx(.24)
    assert r["mix_component"]==pytest.approx(.24)
    assert r["within_state_component"]==0


def test_within_state_lift_is_distinguished_from_composition():
    a={"a":{"weight":.5,"rate":.4},"b":{"weight":.5,"rate":.6}}
    b={"a":{"weight":.5,"rate":.5},"b":{"weight":.5,"rate":.7}}
    r=decompose(a,b)
    assert r["mix_component"]==0 and r["within_state_component"]==pytest.approx(.1)


def test_decomposition_randomized_identity_and_reversal():
    rng=np.random.default_rng(61114)
    for _ in range(50):
        a={str(i):{"weight":float(p),"rate":float(q)} for i,(p,q) in enumerate(zip(rng.dirichlet([2]*4),rng.uniform(size=4)))}
        b={str(i):{"weight":float(p),"rate":float(q)} for i,(p,q) in enumerate(zip(rng.dirichlet([2]*4),rng.uniform(size=4)))}
        x,y=decompose(a,b),decompose(b,a)
        assert x["mix_component"]+x["within_state_component"]==pytest.approx(x["difference"])
        assert x["difference"]==pytest.approx(-y["difference"])


@pytest.mark.parametrize("fault",["state","weight","zero","rate","nan","boolean","metric","horizon","weighting"])
def test_incomparable_or_incomplete_rate_populations_refuse(fault):
    a={"x":{"weight":.5,"rate":.5},"y":{"weight":.5,"rate":.6}}
    b={k:dict(v) for k,v in a.items()};contract=dict(CONTRACT)
    if fault=="state":b.pop("y")
    elif fault=="weight":b["x"]["weight"]=.3
    elif fault=="zero":b["x"]["weight"]=0
    elif fault=="rate":b["x"]["rate"]=1.01
    elif fault=="nan":b["x"]["rate"]=np.nan
    elif fault=="boolean":b["x"]["rate"]=True
    elif fault=="metric":contract["outcome_definition"]="positive_return"
    else:contract[fault]="different"
    with pytest.raises(d.DiagnosticRefusal):decompose(a,b,contract=contract)


def outcomes(gross21=.1,gross63=.32,b21=.02,b63=.08):
    def one(h,r,b):return pd.DataFrame([{"event_id":"fixture","horizon":h,"fill_date":"2018-01-03","price_basis":"synthetic_close", "status":"MATURED","gross_return":float(r),"benchmark_return":float(b)}])
    return one(21,gross21,b21),one(63,gross63,b63)


def test_same_entry_continuation_uses_compounding_not_subtraction():
    a,b=outcomes();r=d.same_entry_horizon_attribution(a,b).iloc[0]
    assert r.continuation_return==pytest.approx(.2)
    assert r.benchmark_continuation_return==pytest.approx(1.08/1.02-1)
    assert (1+r.gross21)*(1+r.continuation_return)-1==pytest.approx(r.gross63)


def test_native_grader_consumer_preserves_exact_fill_and_horizon(prices):
    grid,vix,vvix=prices
    short,long=canonical_outcome(vix,vvix,grid[400],21),canonical_outcome(vix,vvix,grid[400],63)
    a=pd.DataFrame([dict(short,event_id="native_fixture",horizon=21,price_basis="synthetic_close")])
    b=pd.DataFrame([dict(long,event_id="native_fixture",horizon=63,price_basis="synthetic_close")])
    r=d.same_entry_horizon_attribution(a,b).iloc[0]
    assert r.fill_date==str(grid[401].date())
    assert r.continuation_return==pytest.approx(vix.iloc[464]/vix.iloc[422]-1)


@pytest.mark.parametrize("fault",["duplicate","fill","basis","horizon","return","nan"])
def test_horizon_identity_and_numeric_faults_refuse(fault):
    a,b=outcomes()
    if fault=="duplicate":a=pd.concat([a,a],ignore_index=True)
    elif fault=="fill":b.loc[0,"fill_date"]="2018-01-04"
    elif fault=="basis":b.loc[0,"price_basis"]="other_basis"
    elif fault=="horizon":b.loc[0,"horizon"]=42
    elif fault=="return":b.loc[0,"gross_return"]=-1.01
    else:b.loc[0,"gross_return"]=np.nan
    with pytest.raises(d.DiagnosticRefusal):d.same_entry_horizon_attribution(a,b)


def test_unmatched_and_censored_rows_do_not_disappear():
    a,b=outcomes();b.loc[0,"status"]="UNMATURED";b.loc[0,"gross_return"]=np.nan
    r=d.same_entry_horizon_attribution(a,b)
    assert len(r)==1 and r.iloc[0].status=="INCOMPLETE_OR_CENSORED"
    b.loc[0,"event_id"]="other"
    r=d.same_entry_horizon_attribution(a,b)
    assert len(r)==2 and set(r.status)=={"UNMATCHED_HORIZON"}


def test_total_loss_is_not_a_resurrected_winner_or_silently_dropped():
    a,b=outcomes(gross21=-1,gross63=-1)
    r=d.same_entry_horizon_attribution(a,b)
    assert len(r)==1 and r.iloc[0].status=="TOTAL_LOSS_CONTINUATION_UNDEFINED"
    b.loc[0,"gross_return"]=.1
    with pytest.raises(d.DiagnosticRefusal):d.same_entry_horizon_attribution(a,b)


def test_boolean_window_is_not_an_integer_definition():
    with pytest.raises(d.DiagnosticRefusal):d.TrajectorySpec(observation_lag_sessions=True)


def test_source_era_and_absent_clock_origin_are_not_lost(prices):
    grid,vix,vvix=prices;ctx=d.implied_volatility_trajectory(vix,vvix,grid)
    native=event(grid[400],known=False)
    row=d.join_native_event_context([native],ctx)[0]
    assert row["family_first_available"]==native.family_first_available
    assert row["pre_channel_reconstruction"] is True
    assert row["field_origin"]["signal_known_ts"]=="artifact_absent"


def test_context_missing_fields_and_truthy_string_cannot_pass(prices):
    grid,vix,vvix=prices;ctx=d.implied_volatility_trajectory(vix,vvix,grid)
    with pytest.raises(d.DiagnosticRefusal):d.join_native_event_context([event(grid[400])],ctx.drop(columns="feature_session"))
    ctx["trajectory_available"]="False"
    with pytest.raises(d.DiagnosticRefusal):d.join_native_event_context([event(grid[400])],ctx)


def test_fill_session_and_empty_horizon_contract():
    a,b=outcomes();a.loc[0,"fill_date"]=b.loc[0,"fill_date"]="2018-01-06"
    with pytest.raises(d.DiagnosticRefusal):d.same_entry_horizon_attribution(a,b)
    assert list(d.same_entry_horizon_attribution(a.iloc[:0],b.iloc[:0]).columns)[:2]==["event_id","status"]


def synthetic_input_bytes(grid, vix, vvix):
    import io
    result={}
    for path,field,series in (("data/fred/VIXCLS.parquet","vix_close",vix),("data/cboe/vvix.parquet","vvix",vvix)):
        buf=io.BytesIO();series.rename(field).rename_axis("date").to_frame().to_parquet(buf,index=True)
        result[path]=buf.getvalue()
    return result


def test_census_real_consumer_contract_with_synthetic_inputs(tmp_path,monkeypatch,prices):
    import json
    from scripts import prophet_fusion_cohort_census as c
    grid,vix,vvix=prices;raw=synthetic_input_bytes(grid,vix,vvix);reads=[]
    def read(source,path):reads.append(path);return raw[path]
    monkeypatch.setattr(c,"_git_bytes",read)
    out=tmp_path/"census"
    assert c.main(["--start","2018-01-02","--end","2018-12-31","--out",str(out)])==0
    report=json.loads((out/"cohort_context_census.json").read_text())
    assert set(reads)==set(raw)
    assert report["coverage"]["equity_sessions"]>240
    assert report["coverage"]["trajectory_qualified_sessions"]==report["coverage"]["equity_sessions"]
    assert report["outcomes_read"] is False and report["holdout_opened"] is False
    assert report["promotion_eligible"] is False and report["forecast_probability"] is None
    assert all(r["decoded_window"][1] <= "2018-12-31" for r in report["input_receipts"])
    assert "not incremental predictive value" in (out/"cohort_context_census.md").read_text()


@pytest.mark.parametrize("end",["2020-01-02","2023-05-31","2026-11-14"])
def test_census_holdout_refuses_before_source_or_output_access(monkeypatch,tmp_path,end):
    from scripts import prophet_fusion_cohort_census as c
    def forbidden(*args,**kwargs):raise AssertionError("source/output access before cutoff guard")
    monkeypatch.setattr(c,"_git_bytes",forbidden);monkeypatch.setattr(c,"safe_cache",forbidden)
    assert c.main(["--end",end,"--out",str(tmp_path/"not-created")])==2
    assert not (tmp_path/"not-created").exists()


def test_census_post_window_values_are_not_transformed(monkeypatch,prices):
    from scripts import prophet_fusion_cohort_census as c
    grid,vix,vvix=prices
    raw=synthetic_input_bytes(grid,vix,vvix)
    monkeypatch.setattr(c,"_git_bytes",lambda source,path:raw[path])
    before=c.census(start="2018-01-02",end="2018-12-31")
    vix=vix.copy();vvix=vvix.copy()
    # Invalid levels after the declared reader cutoff cannot reach any transform.
    vix.loc[vix.index>"2018-12-31"]=-1000
    vvix.loc[vvix.index>"2018-12-31"]=np.inf
    raw=synthetic_input_bytes(grid,vix,vvix)
    after=c.census(start="2018-01-02",end="2018-12-31")
    for field in ("coverage","direction_counts","opposite_ma_direction_sessions","high_vix_rank_direction_counts"):
        assert before[field]==after[field]
    assert before["input_receipts"][0]["sha256"]!=after["input_receipts"][0]["sha256"]


def test_census_no_runtime_data_or_site_writes(tmp_path,monkeypatch):
    from scripts import prophet_fusion_cohort_census as c
    from scripts.prophet_fusion_arena import OutputPathRefusal
    for name in ("data","site"):
        with pytest.raises(OutputPathRefusal):c.main(["--out",str(c._ROOT/name/"cohort-must-not-write")])


def test_census_direct_file_execution_from_foreign_cwd(tmp_path):
    import os,subprocess,sys
    from pathlib import Path
    script=Path(__file__).resolve().parents[1]/"scripts/prophet_fusion_cohort_census.py"
    env=dict(os.environ);env.pop("PYTHONPATH",None)
    result=subprocess.run([sys.executable,str(script),"--help"],cwd=tmp_path,env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    assert "usage:" in result.stdout


def frozen_horizon_fixture(tmp_path):
    import hashlib
    rows=[]
    for ticker,day,ends in (("EARLY","2018-01-02",("2018-02-02","2018-04-04")),
                            ("CROSS","2019-11-01",("2019-12-03","2020-02-04")),
                            ("SEALED","2020-01-02",("2020-02-04","2020-04-03"))):
        for h,exit_date,r in zip((21,63),ends,(-.1,.1)):
            rows.append({"ticker":ticker,"date":pd.Timestamp(day),"trigger":"fixture_trigger","horizon":h,
                "fill_date":day,"exit_date":exit_date,"status":"MATURED","gross_return":r,
                "benchmark_return":0.,"net_return":r-.0025,"net_excess":r-.0025,
                "forward_mdd_close":-.12 if h==21 else -.18,"forward_mfe_close":.02 if h==21 else .15})
    p=tmp_path/"frozen.parquet";pd.DataFrame(rows).to_parquet(p,index=False)
    return p,hashlib.sha256(p.read_bytes()).hexdigest()


def test_horizon_reader_excludes_labels_crossing_holdout_and_keeps_denominator(tmp_path):
    from scripts import prophet_fusion_horizon_diagnostic as h
    p,digest=frozen_horizon_fixture(tmp_path)
    frame,receipt=h.read_frozen_development_rows(p,digest)
    assert set(frame.ticker)=={"EARLY","CROSS"}
    assert len(frame)==3 and receipt["latest_decoded_outcome_end"]<"2020-01-01"
    report=h.summarize(frame,receipt)
    assert report["pair_status_counts"]=={"PAIRED_GROSS_SEGMENTS":1,"UNMATCHED_HORIZON":1}
    s=report["summaries"][0]
    assert s["positive21"]==0 and s["positive63"]==1
    assert s["negative21_positive63"]==1 and s["positive21_negative63"]==0
    assert s["rate_change_identity_error"]==pytest.approx(0)
    assert s["continuation_return"]==pytest.approx(1.1/.9-1)
    assert report["promotion_eligible"] is False and report["statistical_inference"] is None
    assert "Not grey-dot performance" in h.render(report)


def test_horizon_reader_rejects_changed_frozen_input(tmp_path):
    from scripts import prophet_fusion_horizon_diagnostic as h
    p,digest=frozen_horizon_fixture(tmp_path)
    with pytest.raises(d.DiagnosticRefusal):h.read_frozen_development_rows(p,"0"*64)
    p.write_bytes(p.read_bytes()+b"changed")
    with pytest.raises(d.DiagnosticRefusal):h.read_frozen_development_rows(p,digest)


def test_horizon_cli_uses_original_digest_not_arbitrary_source(tmp_path):
    from scripts import prophet_fusion_horizon_diagnostic as h
    p,_=frozen_horizon_fixture(tmp_path)
    assert h.main(["--events",str(p),"--out",str(tmp_path/"out")])==2
    assert not (tmp_path/"out").exists()


def test_longer_same_entry_path_cannot_have_a_better_worst_loss(tmp_path):
    from scripts import prophet_fusion_horizon_diagnostic as h
    p,digest=frozen_horizon_fixture(tmp_path);frame,receipt=h.read_frozen_development_rows(p,digest)
    frame.loc[frame.horizon.eq(63),"forward_mdd_close"]=-.01
    with pytest.raises(d.DiagnosticRefusal,match="PATH_EXTREMA"):
        h.summarize(frame,receipt)
