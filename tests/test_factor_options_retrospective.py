"""Original synthetic tests for the S3 retrospective research extension."""
from datetime import date, datetime, timezone
from importlib import import_module
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest

MODULE = "research.factor_atlas.session3.retrospective"
ANCHOR = date(2026, 10, 8)
CAPTURED = datetime(2026, 10, 11, 22, tzinfo=timezone.utc)

def test_native_retrospective_module_exists():
    assert (Path(__file__).resolve().parents[1] / "research/factor_atlas/session3/retrospective.py").is_file(), "native retrospective implementation missing"

@pytest.fixture
def m():
    p = Path(__file__).resolve().parents[1] / "research/factor_atlas/session3/retrospective.py"
    assert p.exists(), "native retrospective research implementation missing"
    return import_module(MODULE)

def chain(root="AAA", iv=.2, days=(29,36)):
    rows=[]
    for d in days:
        for right in ["C","P"]:
            rows.append(dict(root=root,date=pd.Timestamp(ANCHOR),expiration=pd.Timestamp(ANCHOR)+pd.Timedelta(days=d),
                             strike=100.,right=right,bid=9.5,ask=10.,underlying_price=100.,implied_vol=iv,iv_error=0.))
    return pd.DataFrame(rows)

def fixtures(n=3):
    roots=[f"R{i:02}" for i in range(n)]
    sessions=pd.bdate_range(end=ANCHOR,periods=270)
    rng=np.random.default_rng(819)
    market=rng.normal(0,.01,len(sessions))
    frame=pd.DataFrame({r:100*np.exp(np.cumsum(market+rng.normal(0,.015,len(sessions)))) for r in roots},index=sessions)
    return dict(weights={r:1/n for r in roots},greeks={r:chain(r,.2+i*.01) for i,r in enumerate(roots)},
                closes=frame,sessions=list(sessions.date),anchor=ANCHOR,captured_at=CAPTURED)

def test_exact_and_bracketed_iv(m):
    assert m.select_iv30(chain(),root="AAA",anchor=ANCHOR)["iv30"] == pytest.approx(.2)
    r=m.select_iv30(chain(days=(30,)),root="AAA",anchor=ANCHOR)
    assert r["iv30"] == pytest.approx(.2)
    assert r["tenors"] == [30]

def test_call_put_mean_variance_not_mean_iv(m):
    f=chain(days=(30,)); f.loc[f.right=="P","implied_vol"] = .4
    assert m.select_iv30(f,root="AAA",anchor=ANCHOR)["iv30"] == pytest.approx(np.sqrt((.2**2+.4**2)/2))

def test_total_variance_interpolation(m):
    f=chain(days=(20,40)); f.loc[f.expiration==pd.Timestamp(ANCHOR)+pd.Timedelta(days=40),"implied_vol"] = .4
    assert m.select_iv30(f,root="AAA",anchor=ANCHOR)["iv30"] == pytest.approx(np.sqrt((.2**2*20+.4**2*40)/60))

@pytest.mark.parametrize("days",[(10,20),(40,50),()])
def test_no_extrapolation(m,days):
    r=m.select_iv30(chain(days=days),root="AAA",anchor=ANCHOR)
    assert r["iv30"] is None

@pytest.mark.parametrize("field,value",[("bid",0),("bid",-1),("ask",9),("ask",50),("implied_vol",0),
    ("implied_vol",float("nan")),("implied_vol",True),("implied_vol","0.2"),("iv_error",1)])
def test_unusable_contracts_withheld(m,field,value):
    f=chain(); f[field]=value
    assert m.select_iv30(f,root="AAA",anchor=ANCHOR)["iv30"] is None

def test_unrepresentable_numeric_source_refused_without_overflow(m):
    giant=10**500
    assert m._numeric(giant) is False
    k=fixtures()
    k["weights"]["R00"]=giant
    with pytest.raises(ValueError,match="positive finite"):
        m.build_study(**k)


def test_call_and_put_must_share_strike(m):
    f=chain(); f.loc[f.right=="P","strike"]=101
    assert m.select_iv30(f,root="AAA",anchor=ANCHOR)["iv30"] is None

def test_duplicate_contract_not_arbitrarily_picked(m):
    f=chain(); f=pd.concat([f,f.iloc[[0]]],ignore_index=True)
    r=m.select_iv30(f,root="AAA",anchor=ANCHOR)
    assert r["iv30"] is None and "DUPLICATE_CONTRACT" in r["reasons"]

def test_nonmatching_root_rejected(m):
    r=m.select_iv30(chain("BBB"),root="AAA",anchor=ANCHOR)
    assert r["iv30"] is None and "ROOT_MISMATCH" in r["reasons"]

def test_heterogeneous_spot_not_hidden_by_median(m):
    f=chain(); f.loc[0,"underlying_price"]=102
    r=m.select_iv30(f,root="AAA",anchor=ANCHOR)
    assert r["iv30"] is None and "INCONSISTENT_SPOT" in r["reasons"]

def test_future_chain_rows_do_not_change_anchor(m):
    f=chain(); future=f.copy(); future.date=pd.Timestamp(ANCHOR)+pd.Timedelta(days=1); future.implied_vol=.8
    assert m.select_iv30(pd.concat([f,future]),root="AAA",anchor=ANCHOR)==m.select_iv30(f,root="AAA",anchor=ANCHOR)

def test_declining_bracket_total_variance_refused(m):
    f=chain(iv=.9); f.loc[f.expiration==pd.Timestamp(ANCHOR)+pd.Timedelta(days=36),"implied_vol"] = .1
    r=m.select_iv30(f,root="AAA",anchor=ANCHOR)
    assert r["iv30"] is None and "DECLINING_TOTAL_VARIANCE" in r["reasons"]

def test_research_model_and_qualified_product_separate(m):
    k=fixtures(); r=m.build_study(**k)
    assert r["coverage"]["count"]==3 and r["coverage"]["weight"]==pytest.approx(1)
    assert r["research"]["mean_iv"] == pytest.approx(.21)
    v=np.log(k["closes"]).diff().tail(252)
    R=v.corr().to_numpy(); weighted=np.array([.2,.21,.22])/3
    assert r["models"]["252"]["move"]==pytest.approx(np.sqrt(weighted@R@weighted*30/365))
    assert r["product"]=={"qualified":False,"headline_iv":None,"expected_move":None}
    assert r["authority"]=={"publication":False,"prophet":False,"position_sizing":False}
    assert r["historical_known_at"] is None
    assert r["captured_at"]==CAPTURED.isoformat()
    json.dumps(r,allow_nan=False)

@pytest.mark.parametrize("missing",[3,4,5])
def test_30_40_50_percent_missing_withholds_entire_model(m,missing):
    k=fixtures(10)
    for root in list(k["weights"])[-missing:]: k["greeks"].pop(root)
    r=m.build_study(**k)
    assert r["coverage"]["count"]==10-missing
    assert r["coverage"]["total_count"]==10
    assert r["coverage"]["weight"]==pytest.approx(1-missing/10)
    assert all(x["move"] is None for x in r["models"].values())
    assert r["research"]["mean_iv"] is not None

def test_missing_price_not_reweighted(m):
    k=fixtures(); k["closes"]=k["closes"].drop(columns="R01")
    r=m.build_study(**k)
    assert all(x["move"] is None for x in r["models"].values())
    assert r["coverage"]["total_count"]==3

def test_price_gap_not_filled_or_bridged(m):
    k=fixtures(); k["closes"].loc[k["closes"].index[-100],"R01"]=np.nan
    r=m.build_study(**k)
    assert r["models"]["63"]["move"] is not None
    assert r["models"]["126"]["move"] is None
    assert "INCOMPLETE_PRICE_WINDOW" in r["models"]["126"]["reasons"]

def test_removed_calendar_row_not_converted_to_multiday_return(m):
    k=fixtures(); k["closes"]=k["closes"].drop(index=k["closes"].index[-10])
    r=m.build_study(**k)
    assert all(x["move"] is None for x in r["models"].values())

def test_future_prices_cannot_affect_research_cutoff(m):
    k=fixtures(); before=m.build_study(**k)
    extra=pd.DataFrame([[1e12,2e12,3e12]],index=[pd.Timestamp(ANCHOR)+pd.Timedelta(days=1)],columns=k["closes"].columns)
    k["closes"]=pd.concat([k["closes"],extra])
    assert m.build_study(**k)==before

def test_calendar_anchor_is_not_silently_shifted(m):
    k=fixtures(); k["sessions"]=k["sessions"][:-1]
    with pytest.raises(ValueError,match="anchor"):m.build_study(**k)

def test_unordered_input_has_identical_result(m):
    k=fixtures(); expected=m.build_study(**k)
    k["closes"]=k["closes"].iloc[::-1,::-1]
    k["weights"]=dict(reversed(list(k["weights"].items())))
    k["greeks"]={r:f.iloc[::-1] for r,f in k["greeks"].items()}
    assert m.build_study(**k)==expected

def test_constant_prices_withhold_correlation(m):
    k=fixtures();k["closes"]["R01"]=100.
    r=m.build_study(**k)
    assert all(x["move"] is None for x in r["models"].values())

def test_duplicate_price_dates_rejected(m):
    k=fixtures();k["closes"]=pd.concat([k["closes"],k["closes"].iloc[[-1]]])
    with pytest.raises(ValueError,match="duplicate"):m.build_study(**k)

@pytest.mark.parametrize("change",["negative_weight","weight_sum","future_anchor","naive_capture","extra_root"])
def test_invalid_contract_refused(m,change):
    k=fixtures()
    if change=="negative_weight":k["weights"]["R00"]=-.1
    if change=="weight_sum":k["weights"]["R00"]=.1
    if change=="future_anchor":k["captured_at"]=datetime(2026,10,7,tzinfo=timezone.utc)
    if change=="naive_capture":k["captured_at"]=datetime(2026,10,11)
    if change=="extra_root":k["greeks"]["EXTRA"]=chain("EXTRA")
    with pytest.raises(ValueError):m.build_study(**k)

@pytest.mark.parametrize("windows",[(True,),(0,),(63,63),(2,)])
def test_invalid_window_contract(m,windows):
    with pytest.raises(ValueError):m.build_study(**fixtures(),windows=windows)

def test_method_and_sensitivity_parameters_returned(m):
    r=m.build_study(**fixtures())
    assert r["method"]["calendar_days"]==30 and r["method"]["year_denominator"]==365
    assert r["method"]["shrinkage_to_identity"]==.1
    assert r["method"]["quote_max_relative_spread"]==.15
    assert r["method"]["membership_basis"]=="retrospective_current_roster"
    assert r["models"]["252"]["shrunken_move"] is not None

def test_nullable_root_cannot_pass_source_identity(m):
    f=chain();f['root']=f['root'].astype('string');f.loc[0,'root']=pd.NA
    r=m.select_iv30(f,root='AAA',anchor=ANCHOR)
    assert r['iv30'] is None and 'ROOT_MISMATCH' in r['reasons']

def test_duplicate_source_columns_withhold_without_crash(m):
    f=chain();f=pd.concat([f,f[['bid']]],axis=1)
    r=m.select_iv30(f,root='AAA',anchor=ANCHOR)
    assert r['iv30'] is None and 'SOURCE_COLUMNS_AMBIGUOUS' in r['reasons']
