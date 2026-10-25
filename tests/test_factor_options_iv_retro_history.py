"""S3 complete-denominator retrospective IV history, synthetic selection inputs."""
from datetime import date, datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
from dataclasses import replace
import math
import numpy as np
import pandas as pd
import pytest

M="research.factor_atlas.session3.retrospective_iv_history"
NOW=datetime(2026,10,11,22,tzinfo=timezone.utc)
DAYS=list(pd.bdate_range(end='2026-10-08',periods=252).date)
ROOTS=['AAA','BBB','CCC']
WEIGHTS={'AAA':.2,'BBB':.3,'CCC':.5}

@pytest.fixture
def m():
    assert (Path(__file__).resolve().parents[1]/'research/factor_atlas/session3/retrospective_iv_history.py').exists(),'native IV-history research module missing'
    return import_module(M)

@pytest.fixture
def rows():
    return {d:{r:{"iv30":.2+.001*i,"reasons":[]} for r in ROOTS} for i,d in enumerate(DAYS)}

def study(m,rows,**kwargs):
    return m.summarize_private_history(sessions=DAYS, weights=WEIGHTS, observed=rows,captured_at=NOW,**kwargs)

def test_252_full_sessions_separates_rank_and_midrank(m,rows):
    result=study(m,rows)
    c=result["coverage"]
    assert c["expected_sessions"]==252 and c["complete_sessions"]==252
    assert c["per_root"]=={r:252 for r in ROOTS}
    assert result["stats"]["iv_rank_minmax_pct"]==pytest.approx(100)
    assert result["stats"]["iv_percentile_midrank_pct"]==pytest.approx((251.5/252)*100)
    assert result["stats"]["current_mean_iv"]==pytest.approx(.451)
    assert result["product"]=={"qualified":False,"iv_rank":None,"iv_percentile":None}
    assert result["historical_known_at"] is None
    assert result["source_type"]=="retrospective_date_only_legacy_options"
    assert result["authority"]=={"publication":False,"prophet":False,"position_sizing":False}

def test_constant_iv_zero_range_rank_none_ties_fifty(m,rows):
    for d in DAYS:
        for r in ROOTS:rows[d][r]["iv30"]=.2
    result=study(m,rows)
    assert result["stats"]["iv_rank_minmax_pct"] is None
    assert result["stats"]["iv_percentile_midrank_pct"]==pytest.approx(50)
    assert "DEGENERATE_IV_RANGE" in result["reasons"]

@pytest.mark.parametrize("missing",[1,3,63,126])
def test_missing_dates_withhold_full_history(m,rows,missing):
    for d in DAYS[-missing:]:rows.pop(d)
    result=study(m,rows)
    assert result["coverage"]["complete_sessions"]==252-missing
    assert result["coverage"]["expected_sessions"]==252
    assert result["stats"]["iv_rank_minmax_pct"] is None
    assert result["stats"]["iv_percentile_midrank_pct"] is None
    assert "INCOMPLETE_SESSION_COVERAGE" in result["reasons"]

@pytest.mark.parametrize("missing", [3,4,5])
def test_missing_names_never_reweight_original_basket(m,rows,missing):
    names=[f'R{i:02}' for i in range(10)]
    weights={r:.1 for r in names}
    d=DAYS[-1]
    cohort={a:{r:{"iv30":.25,"reasons":[]} for r in names} for a in DAYS}
    for r in names[-missing:]:cohort[d].pop(r)
    result=m.summarize_private_history(sessions=DAYS,weights=weights,observed=cohort,captured_at=NOW)
    today=result["series"][-1]
    assert today["covered_count"]==10-missing
    assert today["original_count"]==10
    assert today["covered_weight"]==pytest.approx(1-missing/10)
    assert today["full_basket_mean_iv"] is None
    assert today["eligible_subset_mean_iv"]==pytest.approx(.25)
    assert result["stats"]["iv_rank_minmax_pct"] is None

def test_date_outside_expected_calendar_is_refused(m,rows):
    rows[DAYS[0]-timedelta(days=1)]={}
    with pytest.raises(ValueError,match="outside"):study(m,rows)

def test_unknown_root_is_refused(m,rows):
    rows[DAYS[-1]]["EXTRA"]={"iv30":.9,"reasons":[]}
    with pytest.raises(ValueError,match="root"):study(m,rows)

def test_unusable_iv_bool_nan_negative_and_string_withheld(m,rows):
    for index,value in enumerate([True,float('nan'),-1,"0.4"]):
        rows[DAYS[index]]["AAA"]={"iv30":value,"reasons":[]}
    out=study(m,rows)
    assert out["coverage"]["complete_sessions"]==248
    assert out["coverage"]["per_root"]["AAA"]==248
    assert out["stats"]["iv_percentile_midrank_pct"] is None

def test_unrepresentable_historical_iv_is_coverage_failure_not_crash(m,rows):
    rows[DAYS[3]]['AAA']['iv30']=10**500
    out=study(m,rows)
    assert out['coverage']['complete_sessions']==251
    assert out['stats']['iv_rank_minmax_pct'] is None
    assert out['series'][3]['missing_roots']==['AAA']
    assert out['product']['qualified'] is False


def test_unqualified_source_selection_withholds_name(m,rows):
    d=DAYS[20]
    rows[d]["AAA"]={"iv30":.3,"reasons":["NO_30D_BRACKET"]}
    out=study(m,rows)
    assert out["coverage"]["complete_sessions"]==251
    assert out["series"][20]["missing_roots"]==["AAA"]

def test_future_date_after_capture_cannot_enter(m,rows):
    early=datetime(2026,9,1,18,tzinfo=timezone.utc)
    with pytest.raises(ValueError,match="capture"):m.summarize_private_history(sessions=DAYS,weights=WEIGHTS,observed=rows,captured_at=early)

@pytest.mark.parametrize("problem",["weight_sum","negative","boolean","duplicate_sessions","unordered_sessions","naive_capture"])
def test_contract_inputs_refuse(m,rows,problem):
    weights=WEIGHTS.copy()
    sessions=DAYS.copy()
    capture=NOW
    if problem=="weight_sum":weights["AAA"]=.4
    if problem=="negative":weights["AAA"]=-.2
    if problem=="boolean":weights["AAA"]=True
    if problem=="duplicate_sessions":sessions[-1]=sessions[-2]
    if problem=="unordered_sessions":sessions=sessions[::-1]
    if problem=="naive_capture":capture=NOW.replace(tzinfo=None)
    with pytest.raises(ValueError):
        m.summarize_private_history(sessions=sessions,weights=weights,observed=rows,captured_at=capture)

def test_out_of_order_member_and_date_maps_same_result(m,rows):
    a=study(m,rows)
    backwards={d:dict(reversed(list(roots.items()))) for d,roots in reversed(list(rows.items()))}
    result=m.summarize_private_history(sessions=DAYS,weights=dict(reversed(list(WEIGHTS.items()))),observed=backwards,captured_at=NOW)
    assert result==a

def test_missing_last_session_withholds_current_and_product(m,rows):
    rows.pop(DAYS[-1])
    r=study(m,rows)
    assert r["stats"]["current_mean_iv"] is None
    assert r["stats"]["iv_rank_minmax_pct"] is None
    assert r["product"]["iv_rank"] is None

def test_capture_clock_does_not_pretend_old_availability(m,rows):
    r=study(m,rows)
    assert r["source_quality"]=={"historical_quote_timestamps_available":False,"historical_known_at_certified":False,"price_mark_model_certified":False,"redistribution_rights_certified":False}
    assert all("known_at" not in x for x in r["series"])

def test_full_source_absence_and_tenor_failures_are_separately_accounted(m,rows):
    first=DAYS[3];second=DAYS[14];third=DAYS[20]
    rows[first]={}
    rows[second].pop('AAA')
    rows[third]['BBB']={'iv30':None,'reasons':['NO_30D_BRACKET']}
    result=study(m,rows)
    quality=result['coverage']['failure_diagnostics']
    assert quality['all_root_source_missing_sessions']==[first.isoformat()]
    assert quality['partly_covered_sessions']==[second.isoformat(),third.isoformat()]
    assert quality['missing_by_root']['AAA']==2
    assert quality['missing_by_root']['BBB']==2
    assert quality['missing_by_root']['CCC']==1
    assert quality['failure_reasons']['SOURCE_OR_NAME_MISSING']==4
    assert quality['failure_reasons']['NO_30D_BRACKET']==1

def test_reason_attribution_cannot_modify_complete_statistic(m,rows):
    original=study(m,rows)
    assert original['coverage']['failure_diagnostics']['all_root_source_missing_sessions']==[]
    assert original['coverage']['failure_diagnostics']['failure_reasons']=={}
    assert original['stats']['iv_rank_minmax_pct']==pytest.approx(100)
