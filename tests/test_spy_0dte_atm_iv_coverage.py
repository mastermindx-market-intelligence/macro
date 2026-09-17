import sys
from pathlib import Path

RESEARCH = Path(__file__).parents[1] / "scripts" / "research"
sys.path.insert(0, str(RESEARCH))
import spy_0dte_atm_iv_coverage as c

DATE = "2025-07-01"


def payload(nearest_error=0.0):
    groups = []
    for strike, right, iv in [
        (600, "PUT", .30),
        (600, "CALL", .32),
        (602, "CALL", .80),
    ]:
        data = []
        for i in range(31):
            h = 9 + (30 + i) // 60
            m = (30 + i) % 60
            clock = f"{h:02d}:{m:02d}:00.000"
            error = nearest_error if strike == 600 else 0.0
            data.append({
                "timestamp": DATE + "T" + clock,
                "underlying_timestamp": DATE + "T" + clock,
                "underlying_price": 600 + i * .01,
                "implied_vol": iv - i * .001,
                "iv_error": error,
                "bid": 1.0,
                "ask": 1.1,
            })
        groups.append({
            "contract": {
                "symbol": "SPY",
                "expiration": DATE,
                "strike": strike,
                "right": right,
            },
            "data": data,
        })
    return {"response": groups}


def test_atm_coverage_all_clocks_and_anchor():
    out = c.atm_coverage(payload(), DATE)
    assert out["minute_count"] == 31
    for prefix in ("09:35", "09:45", "10:00"):
        assert out[prefix + "_atm_iv_level"] is True
        assert out[prefix + "_atm_iv_change"] is True
        assert out[prefix + "_anchor_minute"] == 1.0



def test_invalid_underlying_minute_is_counted_missing_without_losing_iv_clocks():
    p = payload()
    for group in p["response"]:
        for row in group["data"]:
            if row["timestamp"].endswith("09:55:00.000"):
                row["underlying_price"] = 0.0
    out = c.atm_coverage(p, DATE)
    assert out["minute_count"] == 30
    for prefix in ("09:35", "09:45", "10:00"):
        assert out[prefix + "_atm_iv_level"] is True
        assert out[prefix + "_atm_iv_change"] is True

def test_invalid_exact_atm_is_missing_even_with_farther_valid_strike():
    out = c.atm_coverage(payload(nearest_error=c.a1.IV_ERROR_MAX + .0001), DATE)
    for prefix in ("09:35", "09:45", "10:00"):
        assert out[prefix + "_atm_iv_level"] is False
        assert out[prefix + "_atm_iv_change"] is False


def test_summary_keeps_partitions_and_errors_separate():
    rows = [
        {
            "date": "2023-01-03",
            "error": None,
            "minute_count": 31,
            **{
                prefix + "_atm_iv_level": True
                for prefix in ("09:35", "09:45", "10:00")
            },
            **{
                prefix + "_atm_iv_change": True
                for prefix in ("09:35", "09:45", "10:00")
            },
        },
        {"date": "2024-07-01", "error": "TimeoutError"},
    ]
    summary = c.summarize(rows)
    assert summary["development"]["09:35_atm_iv_level_available"] == 1
    assert summary["validation"]["errors"] == 1


def test_frozen_residual_boundary_remains_available():
    out = c.atm_coverage(payload(nearest_error=c.a1.IV_ERROR_MAX), DATE)
    for prefix in ("09:35", "09:45", "10:00"):
        assert out[prefix + "_atm_iv_level"] is True
        assert out[prefix + "_atm_iv_change"] is True
