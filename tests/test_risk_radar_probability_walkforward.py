from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.research import risk_radar_probability_walkforward as wf


def test_weighted_pav_is_monotone_and_weighted():
    out = wf.weighted_pav([0.10, 0.30, 0.20, 0.40], [10, 10, 30, 10])
    assert np.all(np.diff(out) >= -1e-12)
    # middle two pool to their weighted mean: (0.3*10 + 0.2*30)/40 = .225
    assert np.allclose(out, [0.10, 0.225, 0.225, 0.40])


def _training_fixture():
    idx = pd.bdate_range("2015-01-02", periods=100)
    states = []
    events = []
    # 20 rows per state, deliberately non-monotone raw rates.
    rates = [0.05, 0.10, 0.20, 0.15, 0.45]
    for name, rate in zip(wf._ORDER, rates):
        states.extend([name] * 20)
        hits = int(round(rate * 20))
        events.extend([True] * hits + [False] * (20 - hits))
    state = pd.Series(states, index=idx)
    labels = pd.DataFrame({
        "end": idx + pd.tseries.offsets.BDay(21),
        "loss": [-0.06 if e else -0.01 for e in events],
        "event": events,
    }, index=idx)
    return state, labels


def test_h21_fit_is_monotone_and_preserves_authority_partition():
    state, labels = _training_fixture()
    fit = wf.fit_state_surface(state, labels, 21)
    vals = [fit["surface"][s] for s in wf._ORDER]
    assert np.all(np.diff(vals) >= -1e-12)
    assert fit["authority_partition_h21"] == {
        "calm": False,
        "watch": False,
        "caution": False,
        "elevated": True,
        "risk-off": True,
    }
    assert max(vals[:3]) <= wf.AUTHORITY_BASE_H21
    assert min(vals[3:]) > wf.AUTHORITY_BASE_H21


def test_training_labels_embargo_forward_outcomes_at_test_start():
    idx = pd.bdate_range("2019-12-20", periods=15)
    state = pd.Series("caution", index=idx)
    labels = pd.DataFrame({
        "end": idx + pd.tseries.offsets.BDay(5),
        "loss": -0.01,
        "event": False,
    }, index=idx)
    first_test = idx[8]
    train = wf._training_labels(labels, state, first_test)
    assert (train.index < first_test).all()
    assert (pd.to_datetime(train["end"]) < first_test).all()
    # At least one earlier forecast date is excluded because its outcome matures after test starts.
    assert len(train) < int((idx < first_test).sum())


def test_candidate_probability_uses_shipped_bump_and_production_cap():
    surface = {s: 0.20 for s in wf._ORDER}
    p1 = wf._candidate_probability("caution", 1, surface, 21)
    p2 = wf._candidate_probability("caution", 2, surface, 21)
    p3 = wf._candidate_probability("caution", 3, surface, 21)
    assert p2 - p1 == round(float(wf._CONJ_BUMP["h21"]), 3)
    assert p3 - p2 == round(float(wf._CONJ_BUMP["h21"]), 3)
    high = {s: 0.94 for s in wf._ORDER}
    assert wf._candidate_probability("risk-off", 5, high, 21) == 0.95


def test_promotion_gate_requires_every_frozen_condition():
    base_result = {
        "paired_brier_delta": -0.001,
        "paired_brier_delta_ci90": [-0.002, -0.0001],
        "current_wace": 0.05,
        "candidate_wace": 0.049,
        "candidate_year_wins": 11,
    }
    results = {h: dict(base_result) for h in ("h5", "h10", "h21")}
    folds = {
        "h5": [{"population_sha256": "a"}],
        "h10": [{"population_sha256": "b"}],
        "h21": [{
            "population_sha256": "c",
            "authority_partition_h21": {
                "calm": False, "watch": False, "caution": False,
                "elevated": True, "risk-off": True,
            },
        }],
    }
    assert wf.promotion_verdict(results, folds)["promotion_eligible"] is True
    harmed = {h: dict(v) for h, v in results.items()}
    harmed["h21"]["paired_brier_delta_ci90"] = [-0.001, 0.0002]
    verdict = wf.promotion_verdict(harmed, folds)
    assert verdict["promotion_eligible"] is False
    assert verdict["checks"]["brier_ci_upper_nonpositive_all"] is False


def test_fold_frame_uses_identical_test_population_for_both_arms(monkeypatch):
    idx = pd.bdate_range("2009-01-02", periods=600)
    # Repeating states guarantees all five appear in training.
    state = pd.Series([wf._ORDER[i % 5] for i in range(len(idx))], index=idx)
    hot = pd.Series([(i % 4) + 1 for i in range(len(idx))], index=idx)
    labels = pd.DataFrame({
        "end": idx + pd.tseries.offsets.BDay(5),
        "loss": [-0.06 if i % 7 == 0 else -0.01 for i in range(len(idx))],
        "event": [i % 7 == 0 for i in range(len(idx))],
    }, index=idx)

    monkeypatch.setattr(
        wf,
        "_drawdown_prob",
        lambda state_name, nhot, calib: {"h5": round(0.05 + 0.01 * nhot, 3)},
    )
    frame, meta = wf.fold_frame(
        state=state, hot_count=hot, labels=labels,
        calib={"sentinel": True}, horizon=5, year=2010,
    )
    assert len(frame) == meta["test_n"]
    assert frame["candidate_probability"].notna().all()
    assert frame["current_probability"].notna().all()
    assert meta["population_sha256"] == wf._fingerprint(labels.loc[frame.index])
    assert pd.Timestamp(meta["train_last_outcome_end"]) < pd.Timestamp(meta["first_test"])
