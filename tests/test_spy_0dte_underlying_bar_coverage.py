import sys
from pathlib import Path

RESEARCH = Path(__file__).parents[1] / "scripts" / "research"
sys.path.insert(0, str(RESEARCH))
import spy_0dte_underlying_bar_coverage as c

DATE = "2023-01-03"


def payload(missing=()):
    rows = []
    missing = set(missing)
    for i in range(30):
        h = 9 + (30 + i) // 60; m = (30 + i) % 60
        clock = f"{h:02d}:{m:02d}:00.000"
        if clock in missing:
            continue
        op = 380 + i * .01; close = op + .01
        rows.append({
            "timestamp": DATE + "T" + clock,
            "open": op, "high": close + .01, "low": op - .01, "close": close,
            "volume": 1000 + i, "count": 100 + i, "vwap": (op + close) / 2,
        })
    return {"response": rows}


def test_complete_opening_window_is_complete_at_all_frozen_clocks():
    out = c.bar_clock_coverage(payload(), DATE)
    assert out["09:35:00.000"]["present_completed_bars"] == 5
    assert out["09:45:00.000"]["present_completed_bars"] == 15
    assert out["10:00:00.000"]["present_completed_bars"] == 30
    assert all(out[clock]["complete"] for clock in c.a1.DECISION_CLOCKS)


def test_missing_0937_does_not_contaminate_0935_but_fails_later_windows_closed():
    out = c.bar_clock_coverage(payload({"09:37:00.000"}), DATE)
    assert out["09:35:00.000"]["complete"] is True
    assert out["09:45:00.000"]["complete"] is False
    assert out["09:45:00.000"]["first_missing"] == "09:37:00.000"
    assert out["10:00:00.000"]["complete"] is False


def test_summary_preserves_partitions_and_errors():
    complete = c.bar_clock_coverage(payload(), DATE)
    rows = [
        {"date": DATE, "partition": "development", "error": None, **complete},
        {"date": "2024-07-01", "partition": "validation", "error": "TimeoutError"},
    ]
    out = c.summarize(rows)
    assert out["development"]["09:35_complete"] == 1
    assert out["development"]["10:00_complete"] == 1
    assert out["validation"]["errors"] == 1


def test_schema_failure_is_explicit_not_imputed(monkeypatch):
    bad = payload(); del bad["response"][0]["vwap"]
    monkeypatch.setattr(c, "_fetch_day", lambda *args: bad)
    out = c.audit_day("http://127.0.0.1:25503/v3", DATE, 1)
    assert out["error"] == "FeatureError"
    assert "09:35:00.000" not in out


def test_live_source_is_localhost_only():
    try:
        c.run_live("https://example.com/v3", 1, 1)
    except c.BarCoverageError as exc:
        assert "localhost" in str(exc)
    else:
        raise AssertionError("non-incumbent source accepted")


def test_summary_contains_no_economic_or_gamma_authority():
    row = {"date": DATE, "partition": "development", "error": None, **c.bar_clock_coverage(payload(), DATE)}
    text = str(c.summarize([row])).lower()
    forbidden = ("pnl", "profit", "outcome", "label", "gamma", "gex", "target", "stop")
    assert not any(token in text for token in forbidden)
