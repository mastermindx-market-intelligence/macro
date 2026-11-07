from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import scripts.research.cn_market_state_validation as p3


def test_prereg_payload_and_manifests_are_fenced():
    doc = p3.verify_prereg()
    assert doc["prereg_payload_sha256"] == (
        "0533cb7add838e65553756e9f21b59b9ff1ae058f347dac0d946da4e977671d8"
    )
    assert doc["sample_end"] == "2026-09-24"


def test_forward_outcome_uses_next_session_not_stamp_close(monkeypatch):
    idx = pd.bdate_range("2026-01-01", periods=50)
    close = pd.Series(np.arange(100.0, 150.0), index=idx)
    monkeypatch.setattr(
        p3.store,
        "read",
        lambda group, name: pd.DataFrame({"close": close})
        if (group, name) == ("china", "000001.SS")
        else None,
    )
    out = p3.build_outcomes("2026-03-31")
    first = out.iloc[0]
    assert first["entry_close"] == close.iloc[1]
    assert first["ret21"] == close.iloc[21] / close.iloc[1] - 1
    assert first["maxdd21"] == 0.0
    assert bool(first["dd21_5pct"]) is False


def test_release_shift_is_strictly_after_calendar_availability():
    sessions = pd.DatetimeIndex(
        pd.to_datetime(["2026-09-15", "2026-09-16", "2026-09-17", "2026-09-18"])
    )
    # August money-supply reference month -> Sep-16 availability -> Sep-17 session.
    s = pd.Series([7.5], index=[pd.Timestamp("2026-08-01")])
    got = p3.shift_series_to_release(s, sessions, "next_month_16")
    assert list(got.index) == [pd.Timestamp("2026-09-17")]
    assert got.iloc[0] == 7.5


def test_blend_renormalizes_over_available_top_level_legs():
    c = pd.DataFrame(
        {"trend": [20.0], "risk": [80.0], "stress": [np.nan]},
        index=[pd.Timestamp("2026-01-02")],
    )
    weights = {"trend": 0.24, "risk": 0.18, "stress": 0.12}
    got = p3.blend_scores(c, weights).iloc[0]
    expected = round((20 * 0.24 + 80 * 0.18) / (0.24 + 0.18))
    assert got == expected


def test_auc_orientation_lower_score_means_higher_risk():
    y = pd.Series([True, True, False, False])
    score = pd.Series([10.0, 20.0, 80.0, 90.0])
    assert p3.roc_auc_binary(y, 100 - score) == 1.0


def test_current_day_reproduces_frozen_market_state():
    prereg = p3.verify_prereg()
    end = pd.Timestamp(prereg["sample_end"])
    f = p3.build_features().loc[:end]
    p3._TREND_FRAME = f
    trend = p3.trend_one_date(end, "US")
    nt, _ = p3.reconstruct_nontrend(f)
    row = nt.loc[end].dropna().astype(int).to_dict()
    row["trend"] = int(trend)
    assert row == prereg["current_model"]["today_orientation"]["components"]

    comp = pd.DataFrame([row], index=[end])
    score = int(p3.build_model_scores(comp, prereg).iloc[0]["current"])
    assert score == prereg["current_model"]["today_orientation"]["raw_score"]


def test_adjudication_never_promotes_reconstructed_evidence():
    p = Path("research/cn_market_state_validation/adjudication.v1.json")
    doc = json.loads(p.read_text())
    assert doc["evidence_class"] == "A_RECONSTRUCTED_HISTORICAL"
    assert doc["rulings"]["SCORE_0_100"] == "DESCRIPTIVE_ONLY"
    assert doc["recommendation"]["production_change"] == "NONE from P3."
