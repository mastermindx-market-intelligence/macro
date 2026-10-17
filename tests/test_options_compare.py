import math
from pathlib import Path

import pandas as pd

from engine import options_compare


ROOT = Path(__file__).resolve().parents[1]


def _latest_from_history(frame, asof, **extra):
    names = {}
    for ticker, group in frame.groupby("underlying"):
        row = group[group["date"].astype(str).str[:10] == asof].iloc[-1]
        names[ticker] = {
            "asof": asof,
            "atm_call_iv": float(row["atm_call_iv"]),
            "skew": float(row["skew"]),
            "tenor_days": float(row["tenor_days"]),
        }
    payload = {
        "ledger_asof": asof,
        "names": names,
        "source_state": "ok",
        "source_detail": {"asof": asof, "stale_days": 0},
        "history_sources": ["thetadata"],
    }
    payload.update(extra)
    return payload


def test_current_session_is_excluded_from_its_own_lookup_window():
    dates = pd.bdate_range("2026-01-02", periods=26)
    rows = []
    for i, stamp in enumerate(dates):
        rows.append(
            {
                "date": stamp,
                "underlying": "AAA",
                "atm_call_iv": 0.15 + i * 0.01,
                "skew": -0.02 + i * 0.002,
                "tenor_days": 30,
            }
        )
    frame = pd.DataFrame(rows)
    asof = dates[-1].date().isoformat()
    result = options_compare.build_compare(
        frame,
        _latest_from_history(frame, asof),
        window=20,
        minimum_history=20,
        trail=5,
    )
    row = result["names"]["AAA"]
    assert row["history_n"] == 20
    assert row["options_pct"] == 100.0
    assert row["protection_pct"] == 100.0


def test_expected_move_uses_selected_tenor_and_annualized_iv():
    dates = pd.bdate_range("2026-01-02", periods=25)
    frame = pd.DataFrame(
        {
            "date": dates,
            "underlying": ["AAA"] * len(dates),
            "atm_call_iv": [0.30] * len(dates),
            "skew": [0.02] * len(dates),
            "tenor_days": [30.0] * len(dates),
        }
    )
    asof = dates[-1].date().isoformat()
    result = options_compare.build_compare(
        frame,
        _latest_from_history(frame, asof),
        minimum_history=20,
        trail=5,
    )
    expected = round(0.30 * math.sqrt(30.0 / 365.0) * 100.0, 1)
    assert result["names"]["AAA"]["expected_move_pct"] == expected
    assert result["names"]["AAA"]["options_pct"] == 50.0


def test_fast_zone_is_top_tenth_by_five_reading_axis_motion():
    dates = pd.bdate_range("2026-01-02", periods=32)
    rows = []
    for index in range(10):
        ticker = f"T{index}"
        for i, stamp in enumerate(dates):
            if index == 0 and i >= 27:
                atm = [0.10, 0.50, 0.10, 0.50, 0.10][i - 27]
                skew = [-0.03, 0.08, -0.03, 0.08, -0.03][i - 27]
            else:
                atm = 0.20 + i * 0.001 + index * 0.0001
                skew = 0.01 + i * 0.0002 + index * 0.00001
            rows.append(
                {
                    "date": stamp,
                    "underlying": ticker,
                    "atm_call_iv": atm,
                    "skew": skew,
                    "tenor_days": 30,
                }
            )
    frame = pd.DataFrame(rows)
    asof = dates[-1].date().isoformat()
    result = options_compare.build_compare(
        frame,
        _latest_from_history(frame, asof),
        window=20,
        minimum_history=20,
        trail=5,
        fast_fraction=0.10,
    )
    assert result["fast_count"] == 1
    assert result["fast_names"] == ["T0"]
    assert result["names"]["T0"]["zone"] == "fast"
    assert all(
        result["names"][f"T{i}"]["zone"] == "calm" for i in range(1, 10)
    )


def test_source_handoff_metadata_is_preserved_for_disclosure():
    dates = pd.bdate_range("2026-01-02", periods=25)
    frame = pd.DataFrame(
        {
            "date": dates,
            "underlying": ["AAA"] * len(dates),
            "atm_call_iv": [0.2 + i * 0.001 for i in range(len(dates))],
            "skew": [0.01 + i * 0.0001 for i in range(len(dates))],
            "tenor_days": [30.0] * len(dates),
        }
    )
    asof = dates[-1].date().isoformat()
    latest = _latest_from_history(
        frame,
        asof,
        source_break=True,
        source_break_date="2026-01-20",
        source_windows=[
            {
                "source": "old",
                "first_date": "2026-01-02",
                "last_date": "2026-01-19",
            }
        ],
        history_sources=["old", "thetadata"],
    )
    result = options_compare.build_compare(
        frame, latest, minimum_history=20, trail=5
    )
    assert result["source_break"] is True
    assert result["source_break_date"] == "2026-01-20"
    assert result["history_sources"] == ["old", "thetadata"]
    assert result["scored"] is False
    assert result["is_context_only"] is True


def test_no_eligible_history_returns_none_instead_of_fake_neutral():
    dates = pd.bdate_range("2026-01-02", periods=10)
    frame = pd.DataFrame(
        {
            "date": dates,
            "underlying": ["AAA"] * len(dates),
            "atm_call_iv": [0.2] * len(dates),
            "skew": [0.01] * len(dates),
            "tenor_days": [30.0] * len(dates),
        }
    )
    asof = dates[-1].date().isoformat()
    assert (
        options_compare.build_compare(
            frame,
            _latest_from_history(frame, asof),
            minimum_history=20,
            trail=5,
        )
        is None
    )


def test_macro_surface_mounts_compare_inside_risk_detail():
    dashboard = (ROOT / "templates" / "dashboard.html.j2").read_text()
    partial = (ROOT / "templates" / "_options_compare.html.j2").read_text()

    assert '{% import "_options_compare.html.j2" as ocx with context %}' in dashboard
    assert "ocx.teaser(options_compare" in dashboard
    assert "ocx.dialog(options_compare" in dashboard
    assert 'id="dlg-options-compare"' in partial
    assert 'id="oc-options-chart"' in partial
    assert "current session never ranks against itself" in partial
    assert "context only; no direction or return forecast" in partial
