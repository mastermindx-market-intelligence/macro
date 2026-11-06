import copy
import json
import pandas as pd
import pytest
from engine.bottom_ruler import grade_call
from research.signal_engine.pivot_replay import evaluate_pivot_calls


def panel():
    dates = pd.bdate_range("2024-01-02", periods=130)
    values = [100 + i * .1 for i in range(130)]
    frame = pd.DataFrame({"close": values, "high": [v+1 for v in values], "low": [v-1 for v in values]}, index=dates)
    frame.attrs["price_basis"] = "adjusted_price"
    return frame


def call(frame, i=20, id="a"):
    day = frame.index[i].date().isoformat()
    return {"id": id, "symbol": "ABC", "signal_date": day,
            "available_at": day + "T17:00:00-05:00", "source_revision": "fixture-v1",
            "price_basis": "adjusted_price", "episode_id": "fixture-episode"}


def run(calls=None, panels=None, **kwargs):
    f = panel()
    return evaluate_pivot_calls(calls if calls is not None else [call(f)],
        panels if panels is not None else {"ABC":f}, evaluation_at=kwargs.pop("evaluation_at", "2024-07-02T23:00:00Z"), **kwargs)


def test_canonical_parity_and_not_provenance_attestation():
    f=panel();r=run()
    assert r["calls"][0]["grade"] == grade_call(f.close, f.high, f.low, call(f)["signal_date"])
    assert r["summary"]["n_graded"] == 1
    assert r["naturally_observed"] is None
    assert r["predictions_qualified"] is False
    assert r["summary"]["event_recall"] is None
    json.dumps(r, allow_nan=False)


@pytest.mark.parametrize("bad", [None, "bad", "2024-07-02", "2024-07-02T12:00:00"])
def test_invalid_cutoff(bad):
    assert run(evaluation_at=bad)["error"] == "invalid_evaluation_contract"


def test_exact_day_delayed_issuance_not_backdated():
    f=panel();c=call(f);c["available_at"] = f.index[22].date().isoformat()+"T17:00:00-05:00"
    assert run([c])["calls"][0]["status"] == "delayed_issuance_requires_execution_model"


def test_same_day_before_close_not_assumed_available():
    f=panel();c=call(f);c["available_at"] = c["signal_date"]+"T12:00:00-05:00"
    assert run([c])["calls"][0]["status"] == "daily_close_not_yet_qualified"


def test_unknown_first_seen_retrospective_only():
    c=call(panel());c.pop("available_at")
    assert run([c])["calls"][0]["status"] == "not_known"
    r=run([c],mode="reconstructed_price_history")
    assert r["calls"][0]["status"] == "graded"
    assert r["naturally_observed"] is False and r["retrospective"] is True


def test_future_receipt_cannot_pass_reconstruction():
    c=call(panel());c["available_at"]="2025-01-01T20:00:00Z"
    assert run([c],mode="reconstructed_price_history")["calls"][0]["status"] == "future_availability"


def test_cutoff_prevents_early_maturity():
    f=panel();evaluation=f.index[80].date().isoformat()+"T23:00:00Z"
    assert run(evaluation_at=evaluation)["calls"][0]["status"] == "immature"


def test_future_prices_not_seen_by_grader():
    f=panel();evaluation=f.index[85].date().isoformat()+"T23:00:00Z"
    seen=[]
    def spy(c,h,l,day):
        seen.extend(c.index);return grade_call(c,h,l,day)
    r=run(panels={"ABC":f},evaluation_at=evaluation,grader=spy)
    assert r["calls"][0]["status"]=="graded"
    assert max(seen) == f.index[84]
    before=copy.deepcopy(r)
    f.loc[f.index[86]:,"close"]=-1000
    assert run(panels={"ABC":f},evaluation_at=evaluation)==before


def test_count_conservation_no_episode_inflation():
    f=panel();calls=[call(f,id=str(i)) for i in range(10)]+[None,call(f,120,"young")]
    r=run(calls);s=r["summary"]
    assert (s["n_submitted"],s["n_graded"],s["n_immature"],s["n_unavailable"])==(12,10,1,1)
    assert s["n_distinct_signal_dates"]==1 and s["n_declared_episodes"]==1


def test_all_duplicate_ids_conflict():
    c=call(panel());r=run([c,dict(c)])
    assert [x["status"] for x in r["calls"]]==["conflict","conflict"]


@pytest.mark.parametrize("what",["missing","basis","unsorted","duplicate","zero","nan","no_close"])
def test_bad_panels(what):
    f=panel();panels={"ABC":f}
    if what=="missing":panels={}
    elif what=="basis":f.attrs["price_basis"]="raw_trade"
    elif what=="unsorted":panels["ABC"]=f.iloc[::-1]
    elif what=="duplicate":panels["ABC"]=pd.concat([f.iloc[:30],f.iloc[29:]])
    elif what=="zero":f.loc[f.index[10],"close"]=0
    elif what=="nan":f.loc[f.index[10],"close"]=float("nan")
    elif what=="no_close":panels["ABC"]=f.drop(columns="close")
    assert run(panels=panels)["summary"]["n_unavailable"]==1


@pytest.mark.parametrize("bad",[None,{}, {"prox":float("nan")},"wrong"])
def test_bad_grade_retained(bad):
    assert run(grader=lambda *args:bad)["summary"]["n_unavailable"]==1


def test_grader_exception_isolated():
    def fail(*a):raise RuntimeError("test")
    assert run(grader=fail)["calls"][0]["status"]=="grade_error"


def test_ohlc_gap_explicit_close_only():
    f=panel();f.loc[f.index[20],"high"]=float("nan")
    r=run(panels={"ABC":f})
    assert r["calls"][0]["grade"]["basis"]=="close_only"


def test_inputs_not_mutated():
    f=panel();c=call(f);saved=f.copy(deep=True);saved_call=copy.deepcopy(c)
    run([c],{"ABC":f})
    pd.testing.assert_frame_equal(f,saved);assert c==saved_call


def test_no_declared_episode_is_unknown_not_zero():
    c=call(panel());c.pop("episode_id")
    assert run([c])["summary"]["n_declared_episodes"] is None


def test_boolean_prices_cannot_be_financial_observations():
    f=panel();f["close"]=True
    assert run(panels={"ABC":f})["calls"][0]["status"]=="invalid_prices"


def test_high_low_must_contain_same_basis_close():
    f=panel();f.loc[f.index[20],'high']=float(f.loc[f.index[20],'close'])-0.1
    assert run(panels={'ABC':f})['calls'][0]['grade']['basis']=='close_only'


def test_floor_window_invalid_range_also_downgrades_to_close_only():
    f=panel();f.loc[f.index[3],'low']=float(f.loc[f.index[3],'close'])+0.1
    assert run(panels={'ABC':f})['calls'][0]['grade']['basis']=='close_only'
