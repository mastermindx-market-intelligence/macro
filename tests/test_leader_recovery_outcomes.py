import pandas as pd
import pytest
from engine.leader_recovery_outcomes import label_recovery_outcome


def case(vals, horizon=3, **kw):
    ix=pd.bdate_range('2026-01-05',periods=len(vals))
    c=pd.Series(vals,index=ix); b=pd.Series(100.,index=ix)
    desc={'as_of':ix[0].date().isoformat(),'state':'REBUILDING',
          'episode':{'peak_price':100.,'price_high_water':110.,'trough_price':50.,'repair_floor':55.}}
    return label_recovery_outcome(c,b,descriptor=desc,sessions=list(ix.date),
            horizon=horizon,available_through=kw.get('through',ix[-1].date()))


def test_complete_upper_crosses_frozen_high_water_not_older_peak():
    a=case([80,101,105,110]);assert a['first_event']=='PRICE_RECOVERED_FIRST'
    assert a['first_event_on']=='2026-01-08'
    assert a['return']==pytest.approx(.375)


def test_failure_wins_even_when_later_higher_price_recovers():
    a=case([80,54,115,120]);assert a['first_event']=='FLOOR_BROKEN_FIRST'
    assert a['mfe_close']==.5 and a['mae_close']==-.325


def test_unresolved_not_permanent_failure():
    a=case([80,80,80,80]);assert a['first_event']=='NO_RESOLUTION_BY_HORIZON'
    assert a['status']=='COMPLETE'


def test_right_censored_not_a_zero_return_or_false_failure():
    a=case([80,85],horizon=3)
    assert a['status']=='RIGHT_CENSORED' and a['return'] is None


def test_gaps_not_filled():
    a=case([80,85,float('nan'),90]);assert a['status']=='DATA_GAP'
    assert a['excess_return'] is None


def test_no_labels_before_future_is_available():
    a=case([80,115,120,140],through=pd.Timestamp('2026-01-05').date())
    assert a['status']=='RIGHT_CENSORED' and a['first_event'] is None


def test_floor_equality_not_breach():
    assert case([80,55,56,60])['first_event']=='NO_RESOLUTION_BY_HORIZON'


def test_already_recovered_requires_another_risk_set():
    result=case([111,112,120,125])
    assert result['event_reason']=='decision_outside_unresolved_price_interval'
    assert result['status']=='COMPLETE'
    assert result['return']==pytest.approx(125/111-1)
    assert result['first_event'] is None


def test_invalid_horizon():
    with pytest.raises(ValueError):case([80,85],horizon=True)


def test_failed_at_decision_is_retained_in_forward_return_sample():
    result=case([54,50,48,40])
    assert result['event_status']=='NOT_AT_RISK'
    assert result['status']=='COMPLETE'
    assert result['return']==pytest.approx(40/54-1)
    assert result['mae_close']==pytest.approx(40/54-1)


def test_known_first_event_survives_later_gap_but_full_horizon_is_unavailable():
    result=case([80,115,float('nan'),120])
    assert result['first_event']=='PRICE_RECOVERED_FIRST'
    assert result['event_status']=='OBSERVED'
    assert result['status']=='DATA_GAP'
    assert result['return'] is None


def test_known_event_and_incomplete_horizon_are_separate():
    result=case([80,115],horizon=3)
    assert result['event_status']=='OBSERVED'
    assert result['first_event']=='PRICE_RECOVERED_FIRST'
    assert result['status']=='RIGHT_CENSORED'
    assert result['return'] is None
