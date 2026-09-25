"""Discriminate frozen gate ablations, decision clocks and inference denominators."""
from copy import deepcopy
from datetime import date
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research/sector_pulse/recommendation_reasons_20260921/compare_entry_gates.py"
spec = importlib.util.spec_from_file_location("entry_gate_comparison", PATH)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def dates(n=650, start="2015-01-02"):
    all_days = pd.date_range(start, periods=n*2, freq="D")
    return pd.DatetimeIndex([d for d in all_days if study.nyse_calendar.is_session(d.date())][:n])


def frames(n=650):
    idx = dates(n)
    t = np.arange(n)
    return {s: pd.DataFrame({"close": 100*np.exp(.0005*t+.025*np.sin(t/(13+j)))}, index=idx)
            for j,s in enumerate((*study.CORE,study.BENCH))}


def decision(rs=.8, extension=1., quality_accel=.6, label="dominant", long_sign=1):
    series=pd.Series(np.linspace(100,140,250))
    fp={"rs_pctile":rs,"accel_z":quality_accel,"long_sign":long_sign}
    bd={"pct50":.8,"nh":3,"nl":0}
    return study.arm_decisions(series,fp,bd,label,.1,50.,extension)


def test_entry_veto_alone_releases_adequate_original_quality():
    r=decision()
    assert r["native_quality"]==pytest.approx(.7)
    assert not r["incumbent"] and r["entry_veto_only"]
    assert not r["recommendation_veto_only"] and r["both_rs_vetoes"]
    assert r["both_with_price_bound"]


def test_recommendation_gate_still_blocks_entry_only_ablation():
    r=decision(rs=.9)
    assert not r["entry_veto_only"] and not r["recommendation_veto_only"]
    assert r["both_rs_vetoes"]


def test_no_counterfactual_quality_bonus_is_awarded():
    r=decision(quality_accel=0)
    assert r["native_quality"] < .6
    assert r["counterfactual_quality"] >= .6
    assert not any(r[k] for k in study.ARMS)


@pytest.mark.parametrize("extension", [None,float("nan"),3.,10.])
def test_price_bound_rejects_unknown_or_stretched_additional_entries(extension):
    r=decision(extension=extension)
    assert r["both_rs_vetoes"] and not r["both_with_price_bound"]


def test_price_bound_does_not_remove_an_incumbent_trade():
    r=decision(rs=.6,extension=20)
    assert all(r[k] for k in study.ARMS)


@pytest.mark.parametrize("label", ["neutral","fading","deteriorating"])
def test_relaxation_does_not_promote_an_unconstructive_label(label):
    assert not any(decision(label=label)[k] for k in study.ARMS)


def test_long_trend_guard_is_preserved():
    assert not any(decision(long_sign=-1)[k] for k in study.ARMS)


def test_native_inputs_are_not_mutated():
    level=pd.Series(np.linspace(100,140,250)); fp={"rs_pctile":.9,"accel_z":.6,"long_sign":1}
    bd={"pct50":.8,"nh":3,"nl":0}; before=(level.copy(),deepcopy(fp),deepcopy(bd))
    study.arm_decisions(level,fp,bd,"dominant",.1,50,1.)
    pd.testing.assert_series_equal(level,before[0]); assert fp==before[1] and bd==before[2]


def test_fixed_universe_is_required():
    raw=frames(70); raw.pop(study.CORE[0])
    with pytest.raises(ValueError,match="all nine"):
        study.prepare_panel(raw)


@pytest.mark.parametrize("defect", ["duplicate","unsorted","negative","infinite","mixed_tail"])
def test_bad_source_frames_are_refused(defect):
    raw=frames(70); key=study.CORE[0]; f=raw[key]
    if defect=="duplicate": raw[key]=pd.concat([f.iloc[:1],f])
    elif defect=="unsorted": raw[key]=f.iloc[::-1]
    elif defect=="negative": raw[key].iloc[5,0]=-1
    elif defect=="infinite": raw[key].iloc[5,0]=np.inf
    elif defect=="mixed_tail": raw[key]=f.iloc[:-1]
    with pytest.raises(ValueError):study.prepare_panel(raw)


def test_missing_expected_session_is_a_hole_not_a_fill():
    raw=frames(70); key=study.CORE[0]; missing=raw[key].index[10]; raw[key]=raw[key].drop(missing)
    panel,meta=study.prepare_panel(raw)
    assert pd.isna(panel.loc[missing,key])
    assert meta[key]["missing_expected_sessions"]==1


def test_non_session_rows_do_not_become_observations():
    raw=frames(70); weekend=pd.Timestamp("2015-01-03")
    for key in raw:raw[key].loc[weekend]=123.; raw[key]=raw[key].sort_index()
    panel,meta=study.prepare_panel(raw)
    assert weekend not in panel.index
    assert all(r["non_session_rows_excluded"]==1 for r in meta.values())


def test_future_prices_cannot_change_earlier_features_or_selections():
    panel,_=study.prepare_panel(frames())
    before,_=study.decision_frame(panel.iloc[:600])
    changed=panel.copy(); changed.iloc[600:]*=4.0
    after,_=study.decision_frame(changed)
    retained=after[after["bar"]<600].reset_index(drop=True)
    pd.testing.assert_frame_equal(before.reset_index(drop=True),retained)


def test_missing_recent_history_refuses_every_proxy_for_that_decision():
    panel,_=study.prepare_panel(frames(530));panel.iloc[500,0]=np.nan
    decisions,refusals=study.decision_frame(panel)
    assert decisions.empty
    assert refusals["incomplete_trailing_native_input_window"]>0


def test_next_close_fill_does_not_capture_the_move_before_entry():
    panel,_=study.prepare_panel(frames(70));key=study.CORE[0]
    panel[:]=100.;panel.loc[panel.index[1]:,key]=120.
    r=study.forward_outcome(panel,key,0,5)
    assert r["net_return"]==pytest.approx(-.002)
    assert r["entry_date"]==str(panel.index[1].date())
    assert r["exit_date"]==str(panel.index[6].date())


def test_horizon_is_counted_after_entry_and_cost_is_round_trip():
    panel,_=study.prepare_panel(frames(70));key=study.CORE[0];panel[:]=100.
    panel.iloc[6,panel.columns.get_loc(key)]=110
    r=study.forward_outcome(panel,key,0,5)
    assert r["net_return"]==pytest.approx(.098)
    assert r["net_relative"]==pytest.approx(.098)
    assert r["mae"]==0


def test_future_missing_bar_is_not_skipped_or_filled():
    panel,_=study.prepare_panel(frames(70));panel.iloc[3,0]=np.nan
    r=study.forward_outcome(panel,study.CORE[0],0,5)
    assert r["status"]=="missing_future_session" and "net_return" not in r


def test_incomplete_tail_is_unknown_not_a_loss_or_zero():
    panel,_=study.prepare_panel(frames(70))
    r=study.forward_outcome(panel,study.CORE[0],60,21)
    assert r["status"]=="tail_unavailable" and "net_return" not in r


def event_rows(n=12):
    rows=[]
    for d in dates(n,start="2019-01-02"):
        for asset in study.CORE:
            r={"decision_date":str(d.date()),"asset":asset,"partition":"assessment","horizon":21,
               "status":"observed","net_return":.1,"net_relative":.09,"mae":-.01,
               **{a:False for a in study.ARMS}}
            r["both_rs_vetoes"]=asset==study.CORE[0]
            r["both_with_price_bound"]=r["both_rs_vetoes"]
            rows.append(r)
    return pd.DataFrame(rows)


def test_inference_counts_dates_not_pooled_assets_and_keeps_fixed_denominator():
    r=study.summarize(event_rows())["partitions"]["assessment"]["21"]
    arm=r["arms"]["both_rs_vetoes"]
    assert arm["paired_vs_incumbent"]["n"]==12
    assert arm["fixed_slot_event_budget_relative_mean"]==pytest.approx(.01)
    assert r["arms"]["incumbent"]["selected"]["net_mean"] is None
    assert r["arms"]["incumbent"]["fixed_slot_event_budget_relative_mean"]==0


def test_missing_asset_outcome_excludes_the_same_date_from_all_arms():
    f=event_rows();f.loc[0,"status"]="missing_future_session"
    r=study.summarize(f)["partitions"]["assessment"]["21"]
    assert r["full_observation_dates"]==11
    assert all(a["paired_vs_incumbent"]["n"]==11 for a in r["arms"].values())


def test_duplicate_event_identity_cannot_inflate_results():
    f=event_rows()
    with pytest.raises(ValueError,match="duplicate event"):
        study.summarize(pd.concat([f,f.iloc[:1]],ignore_index=True))


def test_primary_multiple_testing_family_keeps_all_four_comparisons():
    result=study.summarize(event_rows())
    assert set(result["assessment_primary_bh"])==set(study.ARMS)-{"incumbent"}
    assert result["promotion_authorized"] is False
    json.dumps(result,allow_nan=False)


def test_trials_are_five_frozen_configs_and_not_a_parameter_search(tmp_path):
    configs=[study.fixed_config(a,study.SOURCE_REF) for a in study.ARMS]
    ledger=study.TrialLedger(tmp_path/"trials.jsonl",family=study.FAMILY)
    ledger.log_grid(configs);ledger.log_grid(configs)
    assert ledger.effective_n(study.FAMILY)==5
    assert all(x["round_trip_cost"]==.002 for x in configs)
    assert all(x["extra_entry_extension_lt"]==3 for x in configs)


def test_unfrozen_input_vintage_refuses_before_trial_or_price_access(tmp_path):
    with pytest.raises(ValueError,match="source vintage"):
        study.run("a"*40,tmp_path,"b"*40)


def test_recommendation_only_is_redundant_behind_stricter_entry_gate():
    for rs in np.linspace(0,1,101):
        for label in ("dominant","emerging"):
            r=decision(rs=float(rs),label=label)
            assert r["recommendation_veto_only"]==r["incumbent"]


def test_adverse_excursion_is_from_entry_not_peak_to_trough():
    panel,_=study.prepare_panel(frames(70));key=study.CORE[0];panel[:]=100.
    panel.iloc[2,panel.columns.get_loc(key)]=150
    panel.iloc[3:7,panel.columns.get_loc(key)]=120
    result=study.forward_outcome(panel,key,0,5)
    assert result["mae"]==0  # peak-to-trough is -20%, but entry was never under water
    assert result["mfe"]==pytest.approx(.5)


def test_development_outcomes_cannot_cross_into_assessment():
    idx=dates(130,start="2017-10-02")
    panel=pd.DataFrame(100.,index=idx,columns=(*study.CORE,study.BENCH))
    day=pd.Timestamp("2017-12-20");bar=int(idx.get_loc(day))
    row={"decision_date":str(day.date()),"asset":study.CORE[0],"bar":bar,
         **{a:True for a in study.ARMS}}
    result=study.add_outcomes(panel,pd.DataFrame([row])).set_index("horizon")
    assert result.loc[5,"partition"]=="development"
    assert result.loc[21,"partition"]=="partition_boundary_purged"
    assert result.loc[63,"partition"]=="partition_boundary_purged"
