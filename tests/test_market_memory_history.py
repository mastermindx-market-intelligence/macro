"""Daily historical experience is descriptive, bounded, and outcome-blind."""
from datetime import date, timedelta
import importlib
import importlib.util
import math
import pytest

MODULE = "engine.neuralweb.market_memory_history"

def module():
    assert importlib.util.find_spec(MODULE) is not None, "historical daily experience is not implemented"
    return importlib.import_module(MODULE)

def bars(n=270, start="2015-01-01", multiplier=1.0):
    d = date.fromisoformat(start)
    return [{"market_date": (d + timedelta(days=i)).isoformat(),
             "close_raw": multiplier * (100 + i),
             "close_tradj": multiplier * (50 + i / 2),
             "volume_raw": 1000 + i} for i in range(n)]

def build(data=None, **kwargs):
    opts = dict(start="2015-01-01", end="2015-09-27", benchmark="SPY", basis="tradj")
    opts.update(kwargs)
    return module().build_daily_rows(data or {"SPY": bars(), "QQQ": bars(multiplier=2)}, **opts)

def test_historical_daily_composition_exists():
    assert callable(module().build_daily_rows)

def test_exact_returns_and_warmup():
    rows = build()
    first = next(r for r in rows if r["vendor_symbol"] == "SPY")
    assert first["return_1ob_pct"] is None
    assert first["missing"]["return_1ob_pct"] == "insufficient_history"
    r = next(r for r in rows if r["vendor_symbol"] == "SPY" and r["market_date"] == "2015-03-05")
    assert r["return_63ob_pct"] == pytest.approx(63.0)
    assert r["relative_return_21ob_pp"] == pytest.approx(0.0)
    assert r["sma_distance_20ob_pct"] == pytest.approx((163 / 153.5 - 1) * 100)
    assert r["drawdown_252ob_pct"] is None
    assert "close_tradj" in r and "close_raw" not in r

def test_requested_dates_do_not_discard_warmup():
    full = build()
    sliced = build(start="2015-03-01", end="2015-03-05")
    assert sliced == [r for r in full if "2015-03-01" <= r["market_date"] <= "2015-03-05"]

def test_future_price_and_volume_mutations_cannot_change_past_rows():
    original = {"SPY": bars(), "QQQ": bars(multiplier=2)}
    changed = {s: [dict(r) for r in rs] for s, rs in original.items()}
    for rs in changed.values():
        for r in rs[100:]:
            r["close_tradj"] *= 100
            r["volume_raw"] *= 1000
    a = build(original, end="2015-04-10")
    b = build(changed, end="2015-04-10")
    assert a == b
    assert a == build({s: rs[:100] for s,rs in original.items()}, end="2015-04-10")

def test_duplicate_or_out_of_order_dates_refuse():
    for rows in [bars(5) + [bars(5)[-1]], list(reversed(bars(5)))]:
        with pytest.raises(ValueError, match="strictly increasing"):
            build({"SPY": rows})

@pytest.mark.parametrize("value", [True, -1, 0, float("nan"), float("inf"), "100"])
def test_invalid_price_refuses(value):
    rows = bars(2); rows[0]["close_tradj"] = value
    with pytest.raises(ValueError, match="price"):
        build({"SPY": rows})

def test_null_price_and_volume_are_not_silently_filled():
    rows = bars(25); rows[20]["close_tradj"] = None; rows[21]["volume_raw"] = None
    actual = build({"SPY": rows})
    assert actual[20]["return_1ob_pct"] is None
    assert actual[21]["return_1ob_pct"] is None
    assert actual[21]["volume_ratio_20ob"] is None
    assert actual[21]["sma_distance_20ob_pct"] is None
    assert actual[20]["missing"]["return_1ob_pct"] == "missing_source_value"

def test_benchmark_comparison_uses_matching_endpoint_dates():
    spy = bars(40)
    qqq = bars(40, multiplier=2); del qqq[10]
    result = build({"SPY": spy, "QQQ": qqq})
    r = next(r for r in result if r["vendor_symbol"] == "QQQ" and r["market_date"] == "2015-02-01")
    assert r["relative_return_21ob_pp"] == pytest.approx(0.0)
    assert r["return_21ob_pct"] == pytest.approx((131 / 109 - 1) * 100)

def test_unmatched_benchmark_endpoint_yields_explicit_null():
    spy=bars(40); del spy[10]
    rows=build({"SPY":spy,"QQQ":bars(40,multiplier=2)})
    r=next(r for r in rows if r["vendor_symbol"]=="QQQ" and r["market_date"]=="2015-02-01")
    assert r["relative_return_21ob_pp"] is None
    assert r["missing"]["relative_return_21ob_pp"] == "benchmark_date_missing"

@pytest.mark.parametrize("opts", [{"basis":"close"},{"start":"2016-01-01","end":"2015-01-01"},{"start":"2015-1-1"},{"benchmark":"MISSING"}])
def test_invalid_request_refuses(opts):
    with pytest.raises(ValueError): build(**opts)

def test_outcomes_are_separate_and_censored():
    m=module(); data={"SPY":bars(10)}
    states=build(data)
    assert not any("forward" in k or "outcome" in k for r in states for k in r)
    outcomes=m.build_outcome_rows(data,start="2015-01-01",end="2015-01-10",basis="tradj",horizons=(1,5))
    first=outcomes[0]
    assert first["forward_return_5ob_pct"] == pytest.approx(5)
    assert first["forward_max_drawdown_5ob_pct"] == pytest.approx(0)
    assert outcomes[-1]["forward_return_1ob_pct"] is None
    assert outcomes[-1]["missing"]["forward_return_1ob_pct"] == "right_censored"

def test_outcome_max_drawdown_is_from_entry_not_hindsight_peak():
    rs=bars(4)
    for r,p in zip(rs,[100,120,80,110]): r["close_tradj"]=p
    row=module().build_outcome_rows({"SPY":rs},start="2015-01-01",end="2015-01-01",basis="tradj",horizons=(3,))[0]
    assert row["forward_max_drawdown_3ob_pct"] == pytest.approx(-20)

def test_basis_never_silently_falls_back():
    rs=bars(5)
    for r in rs: r.pop("close_tradj")
    with pytest.raises(ValueError,match="basis"): build({"SPY":rs})

def test_snapshot_does_not_approximate_missing_day():
    m=module(); rows=build({"SPY":bars(3)})
    assert m.select_day(rows,"2015-01-02")[0]["market_date"] == "2015-01-02"
    assert m.select_day(rows,"2015-01-04") == []

def test_size_bounds_and_empty_universe():
    with pytest.raises(ValueError): module().build_daily_rows({},start="2015-01-01",end="2015-01-02",benchmark="SPY",basis="tradj")
    with pytest.raises(ValueError): build({"SPY":bars()},max_total_rows=20)

def test_stable_order_independent_of_symbol_mapping_order():
    assert build({"SPY":bars(5),"QQQ":bars(5)}) == build({"QQQ":bars(5),"SPY":bars(5)})

def test_raw_volume_retains_exact_integer_above_float64_precision():
    rs=bars(2);rs[0]['volume_raw']=9007199254740993
    result=build({'SPY':rs})
    assert result[0]['volume_raw']==9007199254740993
    assert type(result[0]['volume_raw']) is int

@pytest.mark.parametrize('volume',[1.5,2**63,float(2**54),True,-1])
def test_invalid_or_inexact_raw_share_volume_refuses(volume):
    rs=bars(2);rs[0]['volume_raw']=volume
    with pytest.raises(ValueError,match='volume'):build({'SPY':rs})
