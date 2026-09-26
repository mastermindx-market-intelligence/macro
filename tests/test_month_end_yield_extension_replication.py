from __future__ import annotations

import numpy as np
import pandas as pd

from research.rates_direction import month_end_yield_extension_replication as m


def _business_series(start="2026-01-01", end="2026-03-31", *, drift=0.001):
    idx = pd.bdate_range(start, end)
    values = 4.0 + np.arange(len(idx), dtype=float) * drift
    return pd.Series(values, index=idx)


def test_month_end_event_uses_final_observation_and_prior_close_change():
    s = _business_series("2026-01-01", "2026-02-28", drift=0.001)
    # Make January's final observed change distinctly negative.
    jan = s.loc["2026-01"].index
    s.loc[jan[-1]] = s.loc[jan[-2]] - 0.05

    events = m.month_end_events(
        s,
        start=pd.Timestamp("2026-01-01"),
        end=pd.Timestamp("2026-02-28"),
    )
    assert list(events["month"]) == ["2026-01", "2026-02"]
    jan_event = events[events["month"] == "2026-01"].iloc[0]
    assert jan_event.name == jan[-1]
    assert np.isclose(jan_event["raw_bp"], -5.0)
    assert jan_event["n_changes"] >= 5


def test_partial_last_month_is_never_mislabeled_month_end():
    s = _business_series("2026-01-01", "2026-03-20")
    events = m.month_end_events(
        s,
        start=pd.Timestamp("2026-01-01"),
        end=pd.Timestamp("2026-03-20"),
    )
    assert set(events["month"]) == {"2026-01", "2026-02"}
    assert "2026-03" not in set(events["month"])


def test_partial_first_month_is_excluded():
    s = _business_series("2026-01-15", "2026-02-28")
    events = m.month_end_events(
        s,
        start=pd.Timestamp("2026-01-15"),
        end=pd.Timestamp("2026-02-28"),
    )
    assert list(events["month"]) == ["2026-02"]


def test_minimum_monthly_changes_prevents_tiny_month():
    idx = pd.to_datetime(
        [
            "2026-01-27",
            "2026-01-28",
            "2026-01-29",
            "2026-01-30",
            "2026-02-02",
            "2026-02-03",
            "2026-02-04",
            "2026-02-05",
            "2026-02-06",
            "2026-02-09",
        ]
    )
    s = pd.Series(np.linspace(4.0, 4.09, len(idx)), index=idx)
    events = m.month_end_events(
        s,
        start=pd.Timestamp("2026-01-01"),
        end=pd.Timestamp("2026-02-28"),
        minimum_monthly_changes=5,
    )
    # January has only three finite daily changes after the first diff.
    assert "2026-01" not in set(events["month"])


def test_excess_is_raw_minus_same_month_other_day_mean():
    s = _business_series("2026-01-01", "2026-01-31", drift=0.001)
    idx = s.index
    s.loc[idx[-1]] = s.loc[idx[-2]] - 0.02
    events = m.month_end_events(
        s,
        start=pd.Timestamp("2026-01-01"),
        end=pd.Timestamp("2026-01-31"),
    )
    row = events.iloc[0]
    assert np.isclose(
        row["excess_bp"], row["raw_bp"] - row["other_day_mean_bp"]
    )


def test_future_month_mutation_cannot_change_prior_month_event():
    s = _business_series("2026-01-01", "2026-03-31", drift=0.001)
    before = m.month_end_events(
        s,
        start=pd.Timestamp("2026-01-01"),
        end=pd.Timestamp("2026-03-31"),
    )
    changed = s.copy()
    changed.loc["2026-03"] += 1.0
    after = m.month_end_events(
        changed,
        start=pd.Timestamp("2026-01-01"),
        end=pd.Timestamp("2026-03-31"),
    )
    pd.testing.assert_frame_equal(
        before[before["month"].isin(["2026-01", "2026-02"])],
        after[after["month"].isin(["2026-01", "2026-02"])],
    )


def test_split_half_requires_negative_both_halves():
    idx = pd.date_range("2020-01-31", periods=8, freq="ME")
    all_negative = pd.Series([-1.0] * 8, index=idx)
    mixed = pd.Series([-1.0] * 4 + [1.0] * 4, index=idx)
    assert m._split_half(all_negative)["both_negative"] is True
    assert m._split_half(mixed)["both_negative"] is False


def test_evaluate_primary_applies_bh_across_all_eight_cells(monkeypatch):
    idx = pd.date_range("2007-01-31", periods=24, freq="ME")
    fake_events = pd.DataFrame(
        {
            "month": idx.to_period("M").astype(str),
            "n_changes": 20,
            "raw_bp": -1.0,
            "other_day_mean_bp": 0.0,
            "excess_bp": -1.0,
        },
        index=idx,
    )
    fake_events.index.name = "event_date"

    monkeypatch.setattr(m, "month_end_events", lambda *_args, **_kwargs: fake_events.copy())
    out = m.evaluate_primary(
        {tenor: pd.Series([4.0], index=[pd.Timestamp("2007-01-01")]) for tenor in m.TENORS}
    )
    assert set(out["cells"]) == {
        f"{tenor}:{metric}" for tenor in m.TENORS for metric in m.METRICS
    }
    assert all(out["cells"][key]["bh_q"] is not None for key in out["cells"])
    assert out["primary_pass"] is True


def test_spec_keeps_existing_family_and_no_authority():
    assert m.FAMILY == "d2_rates_calendar_flows"
    assert m.PRIOR_FAMILY_TRIALS == 13
    assert len(m.CONFIGS) == 8
    assert m.SPEC["authority"] is False
