from __future__ import annotations

import numpy as np
import pandas as pd

from research.rates_direction import rate_shock_driver_transition as r


def test_driver_state_real_inflation_mixed_conflict():
    assert r._driver_state(1, 20.0, 5.0, 1.5) == "REAL"
    assert r._driver_state(1, 5.0, 20.0, 1.5) == "INFLATION"
    assert r._driver_state(1, 10.0, 9.0, 1.5) == "MIXED"
    assert r._driver_state(1, 10.0, -4.0, 1.5) == "REAL"
    assert r._driver_state(1, -3.0, -4.0, 1.5) == "CONFLICT"
    assert r._driver_state(-1, -20.0, -5.0, 1.5) == "REAL"


def test_state3_is_symmetric_and_unknown_safe():
    assert r._state3(5.0, 5.0, "UP", "DOWN", "FLAT") == "UP"
    assert r._state3(-5.0, 5.0, "UP", "DOWN", "FLAT") == "DOWN"
    assert r._state3(4.9, 5.0, "UP", "DOWN", "FLAT") == "FLAT"
    assert r._state3(float("nan"), 5.0, "UP", "DOWN", "FLAT") == "UNKNOWN"


def _frame(values, barrier=10.0):
    idx = pd.date_range("2025-01-02", periods=len(values), freq="B")
    return pd.DataFrame(
        {
            "nominal": np.asarray(values, dtype=float),
            "barrier_bp": barrier,
        },
        index=idx,
    )


def test_label_event_continuation_and_reversal_mirror():
    up = _frame([4.00, 4.01, 4.03, 4.12] + [4.12] * 8)
    got = r.label_event(up, 0, 1)
    assert got["label"] == "continuation"

    down = _frame([4.00, 3.99, 3.97, 3.88] + [3.88] * 8)
    got2 = r.label_event(down, 0, -1)
    assert got2["label"] == "continuation"

    rev = _frame([4.00, 3.99, 3.89] + [3.89] * 9)
    got3 = r.label_event(rev, 0, 1)
    assert got3["label"] == "reversal"


def test_label_event_no_hit_and_censor():
    nohit = _frame([4.00] + [4.01, 3.99] * 5)
    assert r.label_event(nohit, 0, 1)["label"] == "no_hit"
    short = _frame([4.00] * 5)
    assert r.label_event(short, 0, 1)["label"] == "censored"


def _fake_event(day, direction, label, end, driver="REAL", tp="CONFIRM"):
    return {
        "origin_index": day,
        "origin": pd.Timestamp("2020-01-01") + pd.offsets.BDay(day),
        "direction": direction,
        "driver_state": driver,
        "term_premium_state": tp,
        "credit_state": "FLAT",
        "oil_state": "FLAT",
        "curve_state": "FLAT",
        "auction_state": "NONE",
        "impulse_bp": 20.0 * direction,
        "threshold_bp": 15.0,
        "barrier_bp": 10.0,
        "real_change_bp": 15.0 * direction,
        "be_change_bp": 5.0 * direction,
        "tp_change_bp": 6.0 * direction,
        "hy_change_bp": 0.0,
        "oil_change_pct": 0.0,
        "curve_change_bp": 0.0,
        "outcome": {
            "label": label,
            "target_end_index": end,
            "target_end": (pd.Timestamp("2020-01-01") + pd.offsets.BDay(end)).isoformat(),
            "barrier_bp": 10.0,
        },
    }


def test_forecast_events_purges_unmatured_targets_and_normalizes():
    events = []
    labels = ("continuation", "reversal", "no_hit")
    for i in range(60):
        events.append(_fake_event(i * 12, 1 if i % 2 == 0 else -1, labels[i % 3], i * 12 + 10))
    rows = r.forecast_events(events)
    assert rows
    for row in rows:
        assert pd.Timestamp(row["last_training_target_end"]) < pd.Timestamp(row["origin"])
        for probs in row["probabilities"].values():
            assert np.isclose(sum(probs), 1.0)
            assert all(0 < x < 1 for x in probs)


def test_forecast_is_prefix_invariant_to_future_event_mutation():
    labels = ("continuation", "reversal", "no_hit")
    events = [
        _fake_event(i * 12, 1 if i % 2 == 0 else -1, labels[i % 3], i * 12 + 10)
        for i in range(70)
    ]
    before = r.forecast_events(events)
    mutated = [dict(e) for e in events]
    mutated[-1] = _fake_event(69 * 12, 1, "continuation", 69 * 12 + 10, "INFLATION", "OPPOSE")
    after = r.forecast_events(mutated)
    cutoff = before[-2]["origin"]
    b = [x for x in before if x["origin"] <= cutoff]
    a = [x for x in after if x["origin"] <= cutoff]
    assert b == a


def test_nonoverlap_catalog_contract_with_synthetic_trigger(monkeypatch):
    idx = pd.date_range("2024-01-02", periods=50, freq="B")
    frame = pd.DataFrame(index=idx)
    frame["nominal"] = 4.0 + np.arange(50) * 0.001
    frame["trigger"] = False
    frame.loc[idx[[10, 15, 25]], "trigger"] = True
    frame["impulse_bp"] = 20.0
    frame["real_change_bp"] = 15.0
    frame["be_change_bp"] = 5.0
    frame["tp_change_bp"] = 6.0
    frame["hy_change_bp"] = 0.0
    frame["oil_change_pct"] = 0.0
    frame["curve_change_bp"] = 0.0
    frame["impulse_threshold_bp"] = 15.0
    frame["barrier_bp"] = 10.0

    monkeypatch.setattr(r, "_auction_history", lambda: pd.DataFrame({"auction_date": []}))
    monkeypatch.setattr(r, "_auction_state", lambda scored, date: "NONE")

    def fake_label(f, i, direction):
        return {
            "label": "no_hit",
            "target_end_index": min(len(f) - 1, i + 10),
            "target_end": f.index[min(len(f) - 1, i + 10)].isoformat(),
            "barrier_bp": 10.0,
        }

    monkeypatch.setattr(r, "label_event", fake_label)
    events = r.build_events(frame)
    origins = [e["origin_index"] for e in events]
    assert origins == [10, 25]


def test_rolling_threshold_is_shifted_before_current_observation(monkeypatch):
    # This is a source-code contract rather than opening the real outcomes.
    import inspect
    src = inspect.getsource(r.build_frame)
    assert '["impulse_bp"]' in src
    assert ".abs()" in src
    assert ".shift(1)" in src
    assert '.quantile(SPEC["threshold_quantile"])' in src
