"""Deterministic contracts for descriptive Fear/Greed, not predictive evidence."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine.fear_greed_intelligence import build_intelligence
from engine.vol_velocity import (causal_midrank, compute_vix_dynamics, session_series,
                                 vix_dynamics_frame, volatility_phase)
from lib import nyse_calendar


@pytest.fixture
def inputs():
    dates = pd.DatetimeIndex(nyse_calendar.sessions_between(date(2023, 1, 1), date(2026, 10, 16)))
    x = np.arange(len(dates))
    values = {
        "spy": 100 * np.exp(.0004 * x + .025 * np.sin(x / 24)),
        "tlt": 100 * np.exp(-.0001 * x + .018 * np.cos(x / 17)),
        "vix": 20 + 5 * np.sin(x / 19), "vix3m": 22 + 4 * np.sin(x / 21),
        "vix9d": 19 + 6 * np.sin(x / 19), "vvix": 90 + 15 * np.sin(x / 14),
        "nh": 100 + 50 * np.sin(x / 23), "nl": 80 + 40 * np.cos(x / 29),
        "adv": 1500 + 500 * np.sin(x / 7), "dec": 1500 - 500 * np.sin(x / 7),
        "credit": 4 + np.sin(x / 27), "putcall": .7 + .1 * np.cos(x / 31),
    }
    return {k: pd.Series(v, index=dates) for k, v in values.items()}


def snap(inputs):
    return build_intelligence(inputs, as_of="2026-10-16")


def test_six_family_weights_and_seven_visible_components(inputs):
    p = snap(inputs)
    assert p["status"] == "available"
    assert len(p["components"]) == 7
    assert p["coverage"]["available"] == 6
    assert sum(x["weight"] for x in p["families"]) == pytest.approx(1, abs=1e-5)
    breadth = next(x for x in p["families"] if x["key"] == "participation")
    assert len(breadth["members"]) == 2
    assert breadth["weight"] == pytest.approx(1 / 6, abs=1e-6)
    assert 0 <= p["score"] <= 100
    assert p["score"] == pytest.approx(50 + sum(x["contribution"] for x in p["families"]), abs=.1)
    assert p["forecast_validated"] is False
    assert p["pivot"]["probability"] is None
    json.dumps(p, allow_nan=False)


@pytest.mark.parametrize("v,a,expected", [
    (1, 1, "stress_accelerating"), (1, -1, "stress_decelerating"),
    (-1, -1, "relief_accelerating"), (-1, 1, "relief_decelerating"),
    (0, 0, "steady"), (1, 0, "rising_steady"), (-1, 0, "falling_steady"),
    (np.nan, 1, "unavailable"),
])
def test_direction_and_acceleration_quadrants(v, a, expected):
    assert volatility_phase(v, a) == expected


def test_constant_feed_is_neutral_not_extreme():
    s = pd.Series(np.repeat(20., 300))
    assert causal_midrank(s).iloc[-1] == pytest.approx(50)
    assert causal_midrank(s.iloc[:251]).isna().all()


def test_log_velocity_is_scale_invariant_and_units_exact(inputs):
    dates = inputs["vix"].index
    series = pd.Series(10 * np.exp(.001 * np.arange(len(dates))), index=dates)
    a = compute_vix_dynamics(series, as_of=dates[-1])
    b = compute_vix_dynamics(series * 3, as_of=dates[-1])
    assert a["velocity"] == pytest.approx(.1, abs=1e-4)
    assert a["velocity"] == b["velocity"]
    assert a["acceleration"] == pytest.approx(0, abs=1e-4)
    assert a["change_5d_pct"] == pytest.approx(100 * (np.exp(.005) - 1), abs=.001)


def test_future_prices_never_change_past_snapshot(inputs):
    cutoff = inputs["vix"].index[-61]
    old = build_intelligence(inputs, as_of=cutoff)
    poisoned = {k: s.copy() for k, s in inputs.items()}
    for s in poisoned.values():
        s.loc[s.index > cutoff] *= 1000
    future = build_intelligence(poisoned, as_of=cutoff)
    old.pop("generated_utc")
    future.pop("generated_utc")
    assert old == future


def test_no_missing_partner_as_zero(inputs):
    inputs["nl"].iloc[-1] = np.nan
    inputs["dec"].iloc[-1] = np.nan
    p = snap(inputs)
    for k in ("strength", "breadth"):
        item = next(c for c in p["components"] if c["key"] == k)
        assert item["score"] is None
        assert item["status"] == "stale"
    assert p["change_1d"] is None  # coverage change isn't improving sentiment
    assert p["pivot"]["independent_available"] == 2


def test_insufficient_families_does_not_become_neutral(inputs):
    only_vix = {"vix": inputs["vix"]}
    p = snap(only_vix)
    assert p["score"] is None
    assert p["status"] == "insufficient_data"
    assert p["coverage"]["available"] == 1


def test_all_missing_is_serializable_not_a_fabricated_value():
    p = snap({})
    assert p["score"] is None
    assert p["dynamics"]["status"] == "missing"
    assert p["pivot"]["state"] == "unavailable"
    json.dumps(p, allow_nan=False)


def test_stale_vix_disables_state_and_ratio(inputs):
    p = compute_vix_dynamics(inputs["vix"].iloc[:-1], vix3m=inputs["vix3m"], as_of="2026-10-16")
    assert p["status"] == "stale"
    assert p["phase"] == "unavailable"
    assert p["term_ratio"] is None
    assert p["velocity"] is None


def test_ratio_requires_same_date_and_vvix_is_separate(inputs):
    p = compute_vix_dynamics(inputs["vix"], vix3m=inputs["vix3m"].iloc[:-1],
                             vvix=inputs["vvix"], as_of="2026-10-16")
    assert p["term_ratio"] is None
    assert p["vvix"] == pytest.approx(inputs["vvix"].iloc[-1], abs=.01)
    assert p["vvix"] != p["acceleration"]
    assert p["vvix_status"] == "fresh"


def test_gap_and_invalid_value_reset_derivative(inputs):
    s = inputs["vix"].copy()
    s.iloc[-3] = 0
    out = vix_dynamics_frame(s, "2026-10-16")
    assert pd.isna(out.velocity.iloc[-1])
    assert pd.isna(out.change_5d_pct.iloc[-1])
    assert pd.isna(out.acceleration.iloc[-1])


def test_conflicting_duplicate_is_not_silently_revised(inputs):
    s = inputs["vix"]
    duplicate = pd.concat([s, pd.Series([999.], index=[s.index[-1]])])
    out = session_series(duplicate, "2026-10-16", positive=True)
    assert pd.isna(out.iloc[-1])


def test_weekend_and_future_observations_are_excluded(inputs):
    s = pd.concat([inputs["vix"], pd.Series([999., 999.], index=pd.to_datetime(["2026-10-10", "2026-10-19"]))])
    assert session_series(s, "2026-10-16").equals(session_series(inputs["vix"], "2026-10-16"))


def test_positive_acceleration_does_not_mean_vix_is_rising(inputs):
    s = inputs["vix"].copy()
    s.iloc[-25:] = 40 * np.exp(-.005 * np.arange(25))
    s.iloc[-3:] = [s.iloc[-4] * .999, s.iloc[-4] * .998, s.iloc[-4] * .997]
    p = compute_vix_dynamics(s, as_of="2026-10-16")
    assert p["velocity"] < 0 < p["acceleration"]
    assert p["phase"] == "relief_decelerating"


def test_new_score_does_not_rewrite_existing_machine_dial(monkeypatch):
    import engine.fear_greed as legacy
    import engine.fear_greed_intelligence as intelligence
    monkeypatch.setattr(intelligence, "compute_intelligence", lambda: {"score": 99})
    names = [name for name in vars(legacy) if name.startswith("_leg_")]
    for name in names:
        monkeypatch.setattr(legacy, name, lambda: {"key": "vix_level", "z": 0., "obs_count": 400,
                                                 "freshness": "fresh", "last_date": "2026-10-16"})
    monkeypatch.setattr(legacy, "_young_tile_putcall", lambda: {})
    monkeypatch.setattr(legacy, "_young_tile_aaii", lambda: {})
    p = legacy.compute_fear_greed()
    assert p["dial"] == 50
    assert p["intelligence"]["score"] == 99


@pytest.mark.parametrize("lag,expected", [(1, "delayed"), (2, "delayed"), (3, "insufficient_data")])
def test_dated_snapshot_never_mixes_or_silently_carries_old_data(inputs, lag, expected):
    truncated = {k: s.iloc[:-lag] for k, s in inputs.items()}
    p = snap(truncated)
    assert p["status"] == expected
    if lag <= 2:
        assert p["as_of"] == truncated["spy"].index[-1].strftime("%Y-%m-%d")
        assert p["age_sessions"] == lag
        assert p["dynamics"]["status"] == "stale"
        assert p["pivot"]["state"] == "unavailable"
        assert {c["as_of"] for c in p["components"]} == {p["as_of"]}
    else:
        assert p["score"] is None
        assert p["as_of"] is None


def test_weekend_snapshot_targets_last_actual_session(inputs):
    friday = build_intelligence(inputs, as_of="2026-10-16")
    saturday = build_intelligence(inputs, as_of="2026-10-17")
    friday.pop("generated_utc")
    saturday.pop("generated_utc")
    assert friday == saturday


def test_rank_preserves_isolated_missing_but_expires_ancient_history():
    s = pd.Series(np.arange(600, dtype=float))
    s.iloc[-5] = np.nan
    rank = causal_midrank(s)
    assert pd.notna(rank.iloc[-1])
    assert pd.isna(rank.iloc[-5])
    s.iloc[250:599] = np.nan
    assert pd.isna(causal_midrank(s).iloc[-1])


def test_confirmation_needs_all_three_distinct_families_and_two_closes():
    from engine.fear_greed_intelligence import classify_pivot_context
    d = {"mature": True, "phase": "relief_accelerating", "up_sessions": 0, "down_sessions": 2}
    changes = {"price": 1., "breadth": 1., "credit": -.1, "curve": -.1}
    assert classify_pivot_context(d, changes)["state"] == "relief_broadening"
    assert classify_pivot_context({**d, "down_sessions": 1}, changes)["state"] != "relief_broadening"
    missing_credit = classify_pivot_context(d, {**changes, "credit": None})
    assert missing_credit["state"] == "relief_watch"
    assert missing_credit["independent_available"] == 2
    assert missing_credit["probability"] is None


def test_shock_watch_requires_correct_sign_and_both_extreme_ranks():
    from engine.fear_greed_intelligence import classify_pivot_context
    d = {"mature": True, "phase": "stress_accelerating", "up_sessions": 1, "down_sessions": 0,
         "velocity_percentile": 95., "acceleration_percentile": 95.}
    changes = {"price": None, "breadth": None, "credit": None, "curve": None}
    assert classify_pivot_context(d, changes)["state"] == "shock_watch"
    assert classify_pivot_context({**d, "velocity_percentile": 89}, changes)["state"] != "shock_watch"
    assert classify_pivot_context({**d, "phase": "relief_decelerating"}, changes)["state"] != "shock_watch"


def test_streak_resets_when_raw_close_disagrees_with_smoothed_direction(inputs):
    s = inputs["vix"].copy()
    s.iloc[-20:] = np.linspace(40, 20, 20)
    s.iloc[-1] = s.iloc[-2] * 1.001
    d = compute_vix_dynamics(s, as_of="2026-10-16")
    assert d["velocity"] < 0
    assert d["down_sessions"] == 0


def test_keep_first_ledger_retains_observed_features_not_reconstructed_arrays(inputs, monkeypatch, tmp_path):
    from engine import fear_greed
    monkeypatch.setattr(fear_greed.config, "data_dir", lambda: tmp_path)
    p = {"as_of": "2026-10-16", "dial": 50, "n_legs_qualifying": 5, "label_en": "Neutral",
         "intelligence": snap(inputs)}
    assert fear_greed.persist_dial_history(p) is True
    path = tmp_path / "sentiment_us" / "fear_greed_dial.parquet"
    before = path.read_bytes()
    p["intelligence"]["score"] = 99
    assert fear_greed.persist_dial_history(p) is False
    assert path.read_bytes() == before
    rows = pd.read_parquet(path)
    assert len(rows) == 1
    assert rows.iloc[0].intelligence_version == "mastermind.fear_greed_intelligence.v1"
    observed = json.loads(rows.iloc[0].intelligence_snapshot_json)
    assert "history" not in observed
    assert "history" not in observed["dynamics"]
    assert observed["score"] != 99
    assert len(observed["components"]) == 7


@pytest.mark.parametrize("modern", [True, False])
def test_actual_dashboard_template_renders_new_payload_without_retired_study_route(inputs, modern):
    from tests.test_fear_greed import _make_min_fg, _render_fg_dashboard
    payload = _make_min_fg()
    if modern:
        payload["intelligence"] = snap(inputs)
    dashboard = _render_fg_dashboard(payload)
    assert 'id="fear-greed-dynamics"' in dashboard
    if modern:
        for page in (dashboard,):
            assert 'mastermind.fear_greed_intelligence.v1' in page
            assert 'VIX acceleration' in page
            assert 'VIX 加速度' in page
            assert 'reconstructed' in page.lower()
            assert 'nan' not in page.lower()
            assert 'macro_signals.html#fear-greed-detail' not in page
    else:
        assert 'not available in this published snapshot' in dashboard


def test_replay_episode_cooldown_and_censoring():
    from scripts.research_fear_greed_intelligence import episode_starts, outcomes, summarize
    mask = pd.Series([False] * 70)
    mask.iloc[[0, 1, 10, 21, 22, 45, 69]] = True
    assert episode_starts(mask) == [0, 21, 45, 69]
    rows, censored = outcomes(np.arange(100., 170.), [0, 21, 45, 69], 21)
    assert len(rows) == 3 and censored == 1
    assert summarize(rows, censored)["ci95"] is None


@pytest.mark.parametrize("cache_kind,recomputes", [("legacy", True), ("old_session", True), ("current", False)])
def test_view_cache_upgrades_schema_and_clock_without_publishing(tmp_path, monkeypatch, cache_kind, recomputes):
    from engine import fear_greed
    from scripts import build_site
    from lib import nyse_calendar

    monkeypatch.setattr(build_site.config, "ROOT", tmp_path)
    monkeypatch.setattr(build_site.config, "load", lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda: date(2026, 10, 16))
    cached = {"dial": 42}
    if cache_kind != "legacy":
        cached["intelligence"] = {"schema": "mastermind.fear_greed_intelligence.v1",
                                   "expected_session": "2026-10-16" if cache_kind == "current" else "2026-10-15"}
    path = tmp_path / "site/basketdata/fear_greed.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(cached))
    before = path.read_bytes()
    calls = []
    def compute():
        calls.append(True)
        return {"dial": 43, "intelligence": {"schema": "mastermind.fear_greed_intelligence.v1"}}
    monkeypatch.setattr(fear_greed, "compute_fear_greed", compute)
    result = build_site._fear_greed_view()
    assert len(calls) == int(recomputes)
    assert result["dial"] == (43 if recomputes else 42)
    assert path.read_bytes() == before  # View computation is never another publisher.
