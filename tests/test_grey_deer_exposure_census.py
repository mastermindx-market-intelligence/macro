"""Discriminating census tests; synthetic paths, no historical study rerun."""
import json
import sys

import numpy as np
import pandas as pd
import pytest

from scripts.research import grey_deer_exposure_census as c


def prices(values, start="2020-01-01"):
    idx = pd.bdate_range(start, periods=len(values))
    return pd.DataFrame({"close": values, "close_price": values}, index=idx, dtype=float)


def test_gap_invalidates_prior_future_windows_and_is_not_a_negative():
    frame = prices(np.full(50, 100.0))
    frame.iloc[12] = np.nan
    states = c.origin_states(frame, frame.dropna().index)
    out = c.future_labels(frame.close, states)
    assert out.iloc[9].out_status_5 == "GAP_WINDOW"
    assert pd.isna(out.iloc[9].out_loss_5pct_5)
    assert out.iloc[12].out_status_5 == "ORIGIN_MISSING_SOURCE_SESSION"
    assert out.iloc[13].out_status_5 == "ELIGIBLE"
    assert out.iloc[13].out_loss_5pct_5 == False  # noqa: E712


def test_immaturity_is_not_a_zero_loss_and_never_a_resolved_path():
    frame = prices(np.full(25, 100.0))
    out = c.future_labels(frame.close, c.origin_states(frame, frame.index))
    for h in c.HORIZONS:
        assert out[f"out_status_{h}"].iloc[-h:].eq("IMMATURE_CALENDAR").all()
        assert out[f"out_mfl_{h}"].iloc[-h:].isna().all()
        assert out[f"out_loss_5pct_{h}"].iloc[-h:].isna().all()
    assert out.out_competing_path_21.iloc[-21:].eq("IMMATURE_CALENDAR").all()


def test_simultaneous_recipient_episodes_do_not_create_independent_crises():
    frame = prices(np.r_[np.full(70, 100), [85], np.full(69, 100)])
    a = c.recipient_episodes(frame.close, "A", c.origin_states(frame, frame.index))
    b = c.recipient_episodes(frame.close, "B", c.origin_states(frame, frame.index))
    for h in c.HORIZONS:
        relevant = [e for e in a + b if e["horizon"] == h]
        groups = c.dependence_groups(a + b, h)
        assert len(relevant) == 2
        assert len(groups) == 1
        assert len(groups[0]["recipient_episode_ids"]) == 2
        assert all(e["independence"] == "NOT_ESTABLISHED" for e in relevant)
        assert all(e["known_at"] is None and e["annotation_role"] == "POST_OUTCOME"
                   for e in relevant)


def test_append_future_does_not_rewrite_features_and_basis_is_separate():
    frame = prices(np.linspace(100, 120, 300))
    frame["close"] *= np.linspace(0.7, 1.0, 300)
    prefix = c.observed_features(frame.iloc[:250])
    later = c.observed_features(frame)
    pd.testing.assert_frame_equal(prefix, later.iloc[:250])
    expected_price_dd = frame.close_price.iloc[240] / frame.close_price.iloc[178:241].max() - 1
    assert prefix.iloc[240].obs_price_dd_63 == pytest.approx(expected_price_dd)
    assert prefix.iloc[240].obs_tr_return_5 == pytest.approx(
        frame.close.iloc[240] / frame.close.iloc[235] - 1)


def test_both_down_outperformance_is_not_capital_preservation():
    num, den = -0.02, -0.08
    assert (1 + num) / (1 + den) - 1 > 0
    assert c.rotation_shape(num, den) == "BOTH_DOWN_RELATIVE_COMPARISON_ONLY"
    assert c.rotation_shape(np.nan, den) is None


def test_t12_event_origins_preserved_separately_across_source_gaps():
    frame = prices(np.r_[np.full(70, 100), [80], np.full(70, 100),
                         [np.nan], np.full(70, 100), [80], np.full(70, 100)])
    episodes = c.recipient_episodes(frame.close, "X", c.origin_states(frame, frame.dropna().index))
    labels = c.future_labels(frame.close, c.origin_states(frame, frame.dropna().index))
    for h in c.HORIZONS:
        events = int(labels[f"out_loss_5pct_{h}"].fillna(False).sum())
        assert sum(e["n_event_origins"] for e in episodes if e["horizon"] == h) == events
        assert len([e for e in episodes if e["horizon"] == h]) == 2


def test_precoverage_gaps_stale_ends_remain_in_lattice():
    all_dates = pd.bdate_range("2020-01-01", periods=200)
    original = prices(np.full(100, 100.0), start=str(all_dates[50].date()))
    original = original.drop(original.index[40])
    frame = original.reindex(all_dates)
    states = c.origin_states(frame, original.index)
    assert len(states) == 200
    assert states.value_counts().to_dict() == {
        "OBSERVED": 99, "PRE_SOURCE_COVERAGE": 50,
        "POST_SOURCE_COVERAGE": 50, "MISSING_SOURCE_SESSION": 1,
    }
    obs = c.observed_features(frame)
    assert pd.isna(obs.iloc[50].obs_tr_return_5)
    assert pd.isna(obs.iloc[-1].obs_damage_5pct)


def test_protocol_hash_mismatch_refuses_before_reading_prices(tmp_path, monkeypatch):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"protocol_id": c.PROTOCOL_ID}))
    output = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "census", "--protocol", str(path), "--expected-protocol-sha", "wrong",
        "--source-repo", str(tmp_path), "--output", str(output),
    ])
    with pytest.raises(ValueError, match="PROTOCOL_HASH_MISMATCH"):
        c.main()
    assert not output.exists()


def test_source_hash_mismatch_refuses_before_parquet_decode(tmp_path, monkeypatch):
    monkeypatch.setattr(c.subprocess, "check_output", lambda *a, **kw: b"changed")
    protocol = {
        "source": {"commit": "immutable", "metadata": [{"ticker": "SPY", "sha256": "old"}]},
        "universe": {"SPY": "US"},
    }
    with pytest.raises(ValueError, match="SOURCE_HASH_MISMATCH:SPY"):
        c.load_inputs(tmp_path, protocol)


def test_price_invalid_origin_and_support_cannot_leak_into_episode_counts():
    frame = prices(np.r_[np.full(70, 100), [80], np.full(70, 100)])
    frame.loc[frame.index[68], "close_price"] = 0
    states = c.origin_states(frame, frame.index)
    labels = c.future_labels(frame.close, states)
    episodes = c.recipient_episodes(frame.close, "X", states)
    assert labels.iloc[68].out_status_5 == "ORIGIN_PRICE_INVALID"
    assert labels.iloc[66].out_status_5 == "GAP_WINDOW"
    for h in c.HORIZONS:
        assert int(labels[f"out_loss_5pct_{h}"].fillna(False).sum()) == sum(
            e["n_event_origins"] for e in episodes if e["horizon"] == h)


def test_invalid_spy_history_cannot_make_a_known_broad_gate():
    frame = prices(np.full(230, 100.0))
    frame.iloc[20, frame.columns.get_loc("close")] = 0
    protocol = {
        "calendar": {"start": str(frame.index[0].date()), "cutoff": str(frame.index[-1].date())},
        "universe": {"SPY": "US"},
        "comparisons": {"rotation_pairs": [], "rotation_horizons": [2, 5, 20]},
    }
    rows, _, _, _ = c.build_census({"SPY": frame}, protocol)
    assert pd.isna(rows.iloc[200].obs_spy_gate_component)
    assert rows.iloc[220].obs_spy_gate_component == False  # noqa: E712


def test_changed_reused_method_refuses_before_outcomes(tmp_path, monkeypatch):
    monkeypatch.setattr(c.subprocess, "check_output", lambda *a, **kw: b"different method")
    with pytest.raises(ValueError, match="METHOD_SOURCE_MISMATCH"):
        c.verify_method_dependencies(tmp_path, "frozen")
