"""Pure-function tests for the funding/repo-stress leaf — no network."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import funding_stress as fs  # noqa: E402

_IDX = pd.date_range("2022-01-03", periods=600, freq="B")


def _flat(v):
    return pd.Series(np.full(len(_IDX), float(v)), index=_IDX)


def test_compute_calm_when_spread_low_in_range():
    # spread declines from +10bp to -2bp and dispersion from 20bp to 5bp -> the
    # current reading sits at the BOTTOM of its 2y range -> calm.
    sofr = pd.Series(np.linspace(3.10, 2.98, len(_IDX)), index=_IDX)
    p99 = sofr + np.linspace(0.20, 0.05, len(_IDX))
    out = fs.compute({"sofr": sofr, "effr": _flat(3.00), "sofr_p99": p99},
                     {"pctile_lookback_d": 252})
    assert out["spread_bp"] == -2.0 and out["dispersion_bp"] == 5.0
    assert out["rows"][0]["pctile"] <= 5            # bottom of the window
    assert out["state"] == "calm"


def test_compute_stressed_when_sofr_spikes_above_effr():
    sofr = _flat(3.00).copy()
    sofr.iloc[-1] = 3.30                       # SOFR spikes +30bp over EFFR at the end
    p99 = sofr + 0.02
    p99.iloc[-1] = 3.60                        # right tail blows out too
    out = fs.compute({"sofr": sofr, "effr": _flat(3.00), "sofr_p99": p99},
                     {"pctile_lookback_d": 252})
    assert out["spread_bp"] == 30.0
    assert out["rows"][0]["pctile"] >= 99       # top of the window
    assert out["state"] == "stressed" and out["score"] >= 90


def test_compute_none_without_core_rates():
    assert fs.compute({"sofr": _flat(3.0)}, {}) is None       # no EFFR
    assert fs.compute({}, {}) is None


def test_dispersion_optional():
    out = fs.compute({"sofr": _flat(3.0), "effr": _flat(3.0)}, {"pctile_lookback_d": 252})
    assert out is not None and out["dispersion_bp"] is None    # no SOFR_p99 -> still works


def test_snapshot_degrades(monkeypatch):
    monkeypatch.setattr(fs, "_read", lambda mn: None)
    assert fs.snapshot() is None



def test_short_history_withholds_state_and_keeps_rates():
    for n in range(1, 60):
        for with_dispersion in (False, True):
            sofr = _flat(3.0).iloc[:n]
            d = {'sofr': sofr, 'effr': sofr - .01}
            if with_dispersion:
                d['sofr_p99'] = sofr + .02
            out = fs.compute(d, {})
            assert out['score'] is None and out['state'] is None
            assert out['spread_bp'] == 1.0
            assert len(out['rows']) == (2 if with_dispersion else 1)


def test_sixty_observations_remain_qualified():
    sofr = _flat(3.0).iloc[:60]
    out = fs.compute({'sofr': sofr, 'effr': sofr - .01}, {})
    assert out['score'] == 100 and out['state'] == 'stressed'


def test_funding_tile_unavailable_and_zero_score():
    from jinja2 import Environment
    source = (Path(__file__).resolve().parents[1] / 'templates/crossasset.html.j2').read_text()
    start = source.index('{# Funding tile #}')
    end = source.index('\n</div>\n{% endif %}', start)
    template = Environment(autoescape=True).from_string(source[start:end])
    for lang in (0, 1):
        for score, state in ((None, None), (None, 'calm'), (50, 'unknown')):
            out = template.render(funding={'score': score, 'state': state, 'spread_bp': 1, 'note': ''}, t=lambda en, zh: (en, zh)[lang])
            assert ('Unavailable', '暂无评估')[lang] in out
            assert ('look calm', '市场平静')[lang] not in out
            assert 'var(--muted)' in out
        for score, state, word in ((0, 'calm', ('Calm', '平静')), (70, 'watch', ('Watch', '关注')), (90, 'stressed', ('Stressed', '紧张'))):
            out = template.render(funding={'score': score, 'state': state, 'spread_bp': 1, 'note': ''}, t=lambda en, zh: (en, zh)[lang])
            assert word[lang] in out
            assert ('Unavailable', '暂无评估')[lang] not in out


import json
import pytest

@pytest.mark.parametrize("key", ["sofr", "effr", "sofr_p99"])
@pytest.mark.parametrize("value", [float("inf"),float("-inf"),1e307])
@pytest.mark.parametrize("position", [-1,-20])
def test_nonfinite_operand_or_arithmetic_withholds_assessment(key,value,position):
    d={"sofr":_flat(3),"effr":_flat(2.99),"sofr_p99":_flat(3.02)}
    d[key].iloc[position]=value
    out=fs.compute(d,{"pctile_lookback_d":252})
    assert out["score"] is None and out["state"] is None
    assert out["asof"]==str(_IDX[-1].date())  # never backfill invalid latest
    if key in ("sofr","effr"):
        assert out["spark"]==[]
    if key=="sofr_p99":
        assert out["spread_bp"]==1.0 and out["rows"][0]["pctile"]==100
    if key=="effr":
        assert out["dispersion_bp"]==2.0 and out["rows"][1]["pctile"]==100
    json.dumps(out,allow_nan=False)

def test_invalid_obfr_withholds_only_its_level():
    d={"sofr":_flat(3),"effr":_flat(3),"obfr":_flat(3)}
    expected=fs.compute(d,{})
    d["obfr"].iloc[-1]=float("inf")
    out=fs.compute(d,{})
    assert out["score"]==expected["score"]
    assert next(x for x in out["levels"] if x["key"]=="obfr")["value"] is None
    json.dumps(out,allow_nan=False)

def test_invalid_outside_rank_and_spark_windows_does_not_poison_current():
    d={"sofr":_flat(3),"effr":_flat(3)}
    d["sofr"].iloc[0]=float("inf")
    out=fs.compute(d,{"pctile_lookback_d":252})
    assert out["score"]==100 and out["state"]=="stressed"
    assert out["spark"]==[0.]*252
    json.dumps(out,allow_nan=False)

def test_finite_extreme_spark_range_is_withheld():
    d={"sofr":_flat(0),"effr":_flat(0)}
    d["sofr"].iloc[-2:]=[-1e306,1e306]
    out=fs.compute(d,{})
    assert out["spark"]==[]
    assert out["score"]==100
    json.dumps(out,allow_nan=False)

@pytest.mark.parametrize("key", ["sofr","effr","sofr_p99","obfr"])
def test_native_snapshot_reads_invalid_parquet_without_backfill(tmp_path,monkeypatch,key):
    monkeypatch.setattr(fs.config,"data_dir",lambda:tmp_path)
    d={"sofr":_flat(3),"effr":_flat(2.99),"sofr_p99":_flat(3.02),"obfr":_flat(3)}
    d[key].iloc[-1]=float("inf")
    (tmp_path/"ofr").mkdir()
    for name,series in d.items():
        series.to_frame("value").to_parquet(tmp_path/"ofr"/(fs.SERIES[name]+".parquet"))
    out=fs.snapshot({"pctile_lookback_d":252})
    assert out["asof"]==str(_IDX[-1].date())
    assert out["score"] is None if key!="obfr" else out["score"]==100
    json.dumps(out,allow_nan=False)
