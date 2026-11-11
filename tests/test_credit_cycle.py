"""Pure-function tests for the BIS credit-cycle leaf — no network."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors import bis  # noqa: E402
from engine import credit_cycle as cc  # noqa: E402

_Q = pd.period_range("2010Q1", periods=60, freq="Q").to_timestamp(how="end").normalize()
_CFG = {"boom_gap": 10.0, "delever_gap": -2.0, "countries": {
    "us": {"gap": "us_gap", "dsr": "us_dsr", "label_en": "United States", "label_zh": "美国"},
    "cn": {"gap": "cn_gap", "dsr": "cn_dsr", "label_en": "China", "label_zh": "中国"}}}


def test_parse_period():
    assert bis._parse_period("2025-Q3") == pd.Timestamp("2025-09-30")
    assert bis._parse_period("2025") == pd.Timestamp("2025-12-31")
    assert bis._parse_period("junk") is None


def test_state_thresholds():
    assert cc._state(15.0, _CFG) == "elevated risk"
    assert cc._state(5.0, _CFG) == "building"
    assert cc._state(0.0, _CFG) == "neutral"
    assert cc._state(-6.0, _CFG) == "deleveraging"
    assert cc._state(None, _CFG) == "—"


def test_compute_sorts_and_states():
    series = {
        "us_gap": pd.Series(np.full(60, -12.0), index=_Q),
        "us_dsr": pd.Series(np.full(60, 14.0), index=_Q),
        "cn_gap": pd.Series(np.full(60, 12.0), index=_Q),    # China in boom territory
        "cn_dsr": pd.Series(np.full(60, 19.0), index=_Q),
    }
    out = cc.compute(series, _CFG)
    assert out["rows"][0]["id"] == "cn"                      # highest gap first
    assert out["rows"][0]["gap_state"] == "elevated risk"
    assert out["rows"][1]["gap_state"] == "deleveraging"
    assert out["n_elevated"] == 1 and "1 of 2 elevated" in out["headline"]


def test_compute_change_and_none():
    rising = pd.Series(np.linspace(-12.0, -8.0, 60), index=_Q)   # gap rising +4 over 60q
    out = cc.compute({"us_gap": rising, "us_dsr": pd.Series(np.full(60, 14.0), index=_Q)}, _CFG)
    assert out["rows"][0]["gap_chg_1y"] is not None and out["rows"][0]["gap_chg_1y"] > 0
    assert cc.compute({}, _CFG) is None

# Missing quarters must not change the meaning of a four-quarter comparison.
def test_annual_change_uses_calendar_endpoints():
    q = pd.period_range('2024Q1', periods=6, freq='Q').to_timestamp(how='end').normalize()
    s = pd.Series([12., 0., 1., 2., 3., 4.], index=q)
    assert cc._chg(s) == 4.
    assert cc._chg(s.drop(q[3])) == 4.
    assert cc._chg(s.where(s.index != q[3])) == 4.
    assert cc._chg(s.drop(q[1])) is None
    assert cc._chg(s.loc[[q[1], q[-1]]]) == 4.


def test_annual_change_refuses_ambiguous_calendar():
    assert cc._chg(pd.Series([1., 2.])) is None
    q = pd.to_datetime(['2024-06-01', '2024-06-30', '2025-06-30'])
    assert cc._chg(pd.Series([0., 1., 4.], index=q)) is None
    assert cc._chg(pd.Series([4., 0.], index=q[[2, 0]])) is None



def test_native_bis_store_preserves_calendar_comparison(tmp_path, monkeypatch):
    """Real CSV parser and Parquet store; HTTP/config are synthetic boundaries."""
    from types import SimpleNamespace
    from lib import config, store
    import requests

    cfg = {'storage': {'data_dir': 'data'}, 'credit_cycle': _CFG,
           'bis': {'enabled': True, 'retries': 1, 'series': {
               'us_gap': {'flow': 'WS_CREDIT_GAP', 'key': 'us_gap', 'col': 'value'},
               'us_dsr': {'flow': 'WS_DSR', 'key': 'us_dsr', 'col': 'value'}}}}
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'load', lambda: cfg)
    quarters = ['2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4', '2025-Q1', '2025-Q2']
    values = {'us_gap': [12, 0, 1, 2, 3, 4], 'us_dsr': [22, 10, 11, 12, 13, 14]}

    def response(url, **kwargs):
        key = url.rsplit('/', 1)[-1]
        assert key in values
        # Fresh store, omitted interior quarter: no cache can fill this hole.
        rows = [(q, v) for i, (q, v) in enumerate(zip(quarters, values[key])) if i != 3]
        return SimpleNamespace(status_code=200, text='TIME_PERIOD,OBS_VALUE\n' +
                               ''.join(f'{q},{v}\n' for q, v in rows))

    monkeypatch.setattr(requests, 'get', response)
    result = bis.BisAdapter().fetch()
    assert result['bis_runs']['series_ok'].iloc[0] == 2
    assert len(store.read('bis', 'us_gap')) == 5
    row = cc.snapshot()['rows'][0]
    assert row['gap'] == 4. and row['dsr'] == 14.
    assert row['gap_chg_1y'] == row['dsr_chg_1y'] == 4.
