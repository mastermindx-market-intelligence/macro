"""Killers for the US-side mutants that survive the parity suite (lane MT8).

The cross-market parity suite projects out identity fields and dates by
design, so a defect that moves both markets together -- or only an identity
field -- survives it. These tests drive the real US adapter path
(tests.test_pullback_episode_fuzz._feed: lib.us_pullback_observation.snapshot
then present, over lib.pullback_observation.observe) on fixed synthetic
closes and pin the exact reader numbers. All fixtures are synthetic levels
and are not index quotes.
"""
from __future__ import annotations

from datetime import timezone

from tests import test_pullback_episode_fuzz as us_fuzz

AGE_SERIES = [100.0] * 70 + [94.0, 94.5]
DEPTH_SERIES = [100.0] * 70 + [94.0, 89.731, 91.33]
ARIA_EN = "Observed SPY price closing drawdown from the reference high"
ARIA_ZH = "SPY已观测收盘价相对本轮参考高点的回撤"


def _feed(values):
    obs, _window, view, _qualified, _html = us_fuzz._feed(us_fuzz._zip(values))
    return obs, view


def test_observed_closes_since_onset_is_exact():
    obs, _view = _feed(AGE_SERIES)
    assert obs["observed_closes_since_onset"] == 2


def test_no_new_low_count_is_exact():
    obs, _view = _feed(AGE_SERIES)
    assert obs["no_new_low_closes"] == 1


def test_path_keeps_four_places():
    obs, _view = _feed(DEPTH_SERIES)
    assert obs["price_path"]["vals"][-2] == -10.269


def test_loss_recovered_keeps_two_places():
    obs, _view = _feed(DEPTH_SERIES)
    assert obs["loss_recovered_pct"] == 15.57


def test_recent_63_drawdown_reads_the_recent_high():
    obs, _view = _feed(DEPTH_SERIES)
    assert obs["recent_63_drawdown_pct"] == -8.67


def test_the_measured_chart_is_drawn():
    _obs, view = _feed(DEPTH_SERIES)
    assert view["detail_chart_html"]
    assert view["detail_path"] is not None


def test_us_chart_labels_are_the_us_pair():
    _obs, view = _feed(DEPTH_SERIES)
    assert view["chart_label_en"] == ARIA_EN
    assert view["chart_label_zh"] == ARIA_ZH


def test_valid_until_is_the_next_session_settle():
    obs, _view = _feed(DEPTH_SERIES)
    assert obs["valid_until"] == "2026-06-15T21:00:00+00:00"


def test_produced_at_is_a_utc_stamp():
    obs, _view = _feed(DEPTH_SERIES)
    assert obs["produced_at"] == us_fuzz._NOW.astimezone(timezone.utc).isoformat()


def test_expected_session_is_the_expected_session():
    obs, _view = _feed(DEPTH_SERIES)
    assert obs["expected_session"] == us_fuzz._END.isoformat()
