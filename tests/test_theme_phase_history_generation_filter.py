"""Legacy history semantic admission, including direct callers."""
import datetime as dt
import pytest
from scripts.build_state_of_themes import _compute_weekly_delta

def rows():
    now=dt.datetime.now(dt.timezone.utc)
    return [
        {"schema":"neuralweb.theme_phase_history.v1","theme_id":"a","ts":(now-dt.timedelta(days=1)).isoformat(),"foresight_stage":"WATCH"},
        {"schema":"neuralweb.theme_phase_history.v1","theme_id":"a","ts":now.isoformat(),"foresight_stage":"RE-RATING"},
    ]

@pytest.mark.parametrize("foreign",[None,0,False,[],{},{"schema":"neuralweb.theme_state.v2","theme_id":"a","foresight_stage":"DROP"},{"schema":"neuralweb.theme_phase_history.v2","theme_id":"a","foresight_stage":"DROP"}])
def test_direct_foreign_rows_do_not_change_legacy_delta(foreign):
    positive=rows()
    assert _compute_weekly_delta(positive+[foreign])==_compute_weekly_delta(positive)

def test_real_v1_transition_remains():
    result=_compute_weekly_delta(rows())
    assert result[0] and "WATCH" not in str(result[0])  # existing presentation labels
    assert _compute_weekly_delta([])==([],[])
