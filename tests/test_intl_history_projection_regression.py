from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
import numpy as np
import pandas as pd
import pytest
from engine import international_macro_dashboard as owner
from tests.test_intl_history_read_projection import receipt, history_arguments
from lib.intl_workspace_history import build_history_section


def frame(value, other=0):
    return pd.DataFrame({'growth_score': pd.array([value], dtype=object),
                         'inflation_score': pd.array([other], dtype=object)},
                        index=pd.DatetimeIndex(['2026-01-01T00:00:00.123456789+09:00']))


@pytest.mark.parametrize('value', [True, np.bool_(False), [1, 2], {'private': 5}, object()])
def test_rejected_scalar_uses_fixed_error(value):
    with pytest.raises(ValueError, match='^invalid_history_read_projection$'):
        owner.project_history_read(receipt(frame=frame(value)))


def test_column_extraction_preserves_large_integer_against_float_row_coercion():
    value = pd.DataFrame({'growth_score': pd.array([9007199254740993],dtype='int64'),
                          'inflation_score': [0.5]}, index=frame(0).index)
    output=owner.project_history_read(receipt(frame=value))
    assert type(output['points'][0]['growth_score']) is int
    assert output['points'][0]['growth_score']==9007199254740993
    assert output['points'][0]['inflation_score']==0.5
    assert build_history_section(**history_arguments(output))['points'][0]['growth_score']==9007199254740993


@pytest.mark.parametrize('overrides', [
    {'status': []}, {'read_at':'invalid'}, {'read_at':'2026-01-01T00:00:00'},
    {'market_id':' JP'}, {'method_ref':'\tmethod'},
    {'artifact_ref':'x\\y'}, {'artifact_ref':'x\x00y'}, {'artifact_ref':'a/../b'},
])
def test_malformed_metadata_has_fixed_error(overrides):
    value = receipt(frame=frame(1))
    value.update(overrides)
    with pytest.raises(ValueError, match='^invalid_history_read_projection$'):
        owner.project_history_read(value)


def test_custom_numeric_cannot_execute_conversion():
    calls=[]
    class Evil(int):
        def __int__(self):
            calls.append('int')
            return 77
    class Other(float):
        def __float__(self):
            calls.append('float')
            return 77.0
    for value in [Evil(5),Other(5.0)]:
        with pytest.raises(ValueError,match='^invalid_history_read_projection$'):
            owner.project_history_read(receipt(frame=frame(value)))
    assert calls==[]


def test_nanosecond_clock_and_observation_reach_accepted_helper_unchanged():
    clock='2026-10-08T01:02:03.000456789+05:30'
    output=owner.project_history_read(receipt(frame=frame(1),read_at=clock))
    view=build_history_section(**history_arguments(output))
    assert view['acquisition_at']==clock
    assert view['points'][0]['observation_at']=='2026-01-01T00:00:00.123456789+09:00'
