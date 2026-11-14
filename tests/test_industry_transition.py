import numpy as np
import pandas as pd
import pytest
from dataclasses import replace
from engine.industry_transition import (CLASSES, CONTEXT_FEATURES, PRICE_FEATURES, Config,
    ResearchModel, forecast_record, make_events, make_features, selected, summarize)


@pytest.fixture(scope="module")
def panel():
    rng = np.random.default_rng(71); dates = pd.bdate_range("1985-01-01", periods=900)
    m = pd.Series(rng.normal(.0002, .008, len(dates)), index=dates)
    r = pd.DataFrame(m.to_numpy()[:, None] * np.linspace(.5, 1.5, 25) + rng.normal(0, .006, (len(dates), 25)),
                     index=dates, columns=[f"g{i:02d}" for i in range(25)])
    f = pd.DataFrame({"RF": .0001, "SMB": rng.normal(0, .003, len(dates)),
                      "HML": rng.normal(0, .003, len(dates))}, index=dates)
    return r, m, f


def test_prefix_invariance(panel):
    r, m, f = panel
    whole = make_features(r, m, f)
    partial = make_features(r.iloc[:600], m.iloc[:600], f.iloc[:600])
    a = whole[whole.decision_date <= r.index[599]].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, partial)


def test_calendar_and_duplicate_rejection(panel):
    r, m, f = panel
    with pytest.raises(ValueError, match="calendar"): make_features(r, m.iloc[1:], f)
    with pytest.raises(ValueError, match="unique"): make_features(pd.concat([r, r.iloc[[-1]]]), m, f)


def test_missing_price_never_forward_filled(panel):
    r, m, f = panel
    bad = r.copy(); bad.iloc[500, 0] = np.nan
    features = make_features(bad, m, f)
    row = features[(features.decision_date == r.index[510]) & (features.industry == "g00")].iloc[0]
    assert np.isnan(row.relative21) and np.isnan(row.drawdown126)
    assert row.state == "unavailable"


def test_missing_macro_stays_missing(panel):
    r, m, _ = panel
    f = make_features(r, m)
    assert f.cash_rate.isna().all() and f.smb63.isna().all()


def test_industry_state_partition_and_probable_exposure(panel):
    r, m, f = panel
    features = make_features(r, m, f)
    last = features[features.decision_date == r.index[-1]]
    assert set(last.state).issubset({"continuation", "reversal_attempt", "deterioration", "persistent_weakness"})
    assert np.isfinite(last[list(CONTEXT_FEATURES)]).all().all()
    assert 0 <= last.participation21.iloc[0] <= 1


def test_event_entry_and_first_passage(panel):
    r, m, f = panel
    features = make_features(r, m, f); config = Config(horizon=10)
    events = make_events(r, m, features, config)
    assert not events.empty
    row = events.iloc[3]
    entry = r.index.get_loc(row.decision_date) + 1
    values = r[row.industry].iloc[entry + 1:entry + 11]
    path = (1 + values).cumprod() - 1
    assert row.entry_date == r.index[entry]
    assert row.label_end == r.index[entry + 10]
    assert row.terminal_net == pytest.approx(path.iloc[-1] - config.cost)
    assert row.adverse_excursion == pytest.approx(min(0, path.min()))
    u, d = np.flatnonzero(path >= .1), np.flatnonzero(path <= -.1)
    tu, td = (u[0] if len(u) else 10), (d[0] if len(d) else 10)
    assert row.outcome == (0 if tu < td else 1 if td < tu else 2)


def artificial_events():
    rng = np.random.default_rng(14); rows = []
    for dt in pd.date_range("1960-01-31", "1982-12-31", freq="ME"):
        for i in range(6):
            row = {name: float(rng.normal()) for name in CONTEXT_FEATURES}
            row.update(decision_date=dt, industry=f"i{i}", entry_date=dt + pd.Timedelta(days=1),
                       label_end=dt + pd.Timedelta(days=90), state="continuation",
                       outcome=int(rng.integers(3)), bad_loss=int(rng.uniform() < .3),
                       excess_net=float(rng.normal(.01, .06)), terminal_net=float(rng.normal(.02, .08)),
                       adverse_excursion=-float(rng.uniform(0, .2)))
            rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def fitted():
    events = artificial_events(); start = pd.Timestamp("1982-01-01")
    cut = pd.Timestamp("1979-01-01")
    train = events[events.label_end < cut]
    cal = events[(events.decision_date >= cut) & (events.label_end < start)]
    model = ResearchModel(PRICE_FEATURES).fit(train, cal, start)
    return events, model, train, cal


def test_competing_probabilities_and_separate_risk(fitted):
    events, model, _, _ = fitted
    test = events[events.decision_date >= "1982-01-01"]
    p = model.predict(test)
    np.testing.assert_allclose(p[["p_" + x for x in CLASSES]].sum(axis=1), 1)
    assert p.p_bad_loss.between(0, 1).all()
    assert p.outside_support_share.between(0, 1).all()
    assert np.isfinite(p.expected_excess_net).all()


def test_model_cannot_read_calibration_future(fitted):
    events, _, train, cal = fitted
    bad = train.copy(); bad.iloc[-1, bad.columns.get_loc("label_end")] = pd.Timestamp("1981-01-01")
    with pytest.raises(ValueError, match="overlap"):
        ResearchModel(PRICE_FEATURES).fit(bad, cal, pd.Timestamp("1982-01-01"))
    bad = cal.copy(); bad.iloc[-1, bad.columns.get_loc("label_end")] = pd.Timestamp("1982-03-01")
    with pytest.raises(ValueError, match="matured"):
        ResearchModel(PRICE_FEATURES).fit(train, bad, pd.Timestamp("1982-01-01"))


def test_prediction_does_not_use_future_labels(fitted):
    events, model, _, _ = fitted
    test = events[events.decision_date >= "1982-01-01"]
    a = model.predict(test)
    b = test.copy(); b["outcome"] = 99; b["bad_loss"] = 99; b["excess_net"] = 999
    b = model.predict(b)
    np.testing.assert_array_equal(a[["p_" + x for x in CLASSES]], b[["p_" + x for x in CLASSES]])


def test_prediction_boundary_and_missing_features(fitted):
    events, model, _, _ = fitted
    with pytest.raises(ValueError, match="before"): model.predict(events.head(1))
    row = events[events.decision_date >= "1982-01-01"].head(1).copy(); row["relative21"] = np.nan
    with pytest.raises(ValueError, match="nonfinite"): model.predict(row)


def test_equal_coverage_tie_breaking(fitted):
    events, model, _, _ = fitted
    test = events[events.decision_date >= "1982-01-01"]
    scored = model.predict(test); scored["score"] = 0
    take = selected(scored, .2)
    assert set(take.groupby("decision_date").size()) == {2}
    assert set(take.industry) == {"i0", "i1"}


def test_record_is_research_with_horizon_and_identity(fitted):
    events, model, _, _ = fitted
    row = events[events.decision_date >= "1982-01-01"].head(1)
    record = forecast_record(model, row, "sourcehash", "RECONSTRUCTED_DISCOVERY")
    assert not record["financial_influence"] and len(record["record_id"]) == 64
    assert len(record["explanation"]) == 5
    assert record == forecast_record(model, row, "sourcehash", "RECONSTRUCTED_DISCOVERY")
    with pytest.raises(ValueError): forecast_record(model, row, "sourcehash", "LIVE_VALIDATED")


def test_summary_partition(fitted):
    events, model, _, _ = fitted
    summary = summarize(model.predict(events[events.decision_date >= "1982-01-01"]))
    assert sum(summary[c] for c in CLASSES) == pytest.approx(1)
    assert 0 <= summary["brier_multiclass"] <= 2


@pytest.mark.parametrize("kwargs", [{"horizon": 0}, {"entry_delay": 0}, {"target": 0}, {"loss": 2}, {"cost": -1}, {"regularization": 0}, {"selection_fraction": 2}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError): Config(**kwargs)


def test_numeric_model_artifact_round_trip_and_tamper(fitted):
    from copy import deepcopy
    events, model, _, _ = fitted
    test = events[events.decision_date >= "1982-01-01"].head(10)
    artifact = model.to_artifact()
    loaded = ResearchModel.from_artifact(artifact)
    np.testing.assert_allclose(model.predict(test).p_upside_first, loaded.predict(test).p_upside_first)
    altered = deepcopy(artifact); altered["arrays"]["coef"][0][0] += 1
    with pytest.raises(ValueError, match="digest"): ResearchModel.from_artifact(altered)
