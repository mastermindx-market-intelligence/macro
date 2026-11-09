"""The theme tape's clock, not archive tail/build time, anchors rotation deltas.

These are source-integrity discriminators, not evidence of investment alpha.
All sources are injected; nothing fetches prices or writes a forward ledger.
"""
from copy import deepcopy

import pytest

from engine import sector_pulse as sp


def theme(rank=5, score=65):
    return {"id": "leader", "name": "Leader", "name_zh": "领涨板块",
            "rank": rank, "score": score, "label": "dominant", "reco": "hold"}


def snapshot(asof, rank=9, score=60):
    return {"asof": asof, "themes": [theme(rank, score)]}


def pulse(monkeypatch, snapshots, *, asof="2026-09-18", region="us"):
    current = {"as_of": asof, "themes": [theme()]}
    monkeypatch.setattr(sp, "_load_theme_intel", lambda _: current)
    monkeypatch.setattr(sp, "_load_archive_snapshots", lambda _: snapshots)
    monkeypatch.setattr(sp, "_heat_calibration", lambda: {})
    return sp.build_pulse(region)


def test_future_archive_never_changes_an_older_theme_read(monkeypatch):
    history = [snapshot("2026-09-16", 11), snapshot("2026-09-17", 9),
               snapshot("2026-09-18", 5)]
    expected = pulse(monkeypatch, history)
    actual = pulse(monkeypatch, history + [snapshot("2026-09-21", 1),
                                         snapshot("2026-09-22", 20)])
    assert actual == expected
    assert actual["themes"][0]["rank_delta_1d"] == 4


def test_current_theme_is_the_anchor_before_its_archive_row_exists(monkeypatch):
    result = pulse(monkeypatch, [snapshot("2026-09-16", 11),
                                snapshot("2026-09-17", 9)])
    assert result["themes"][0]["rank_delta_1d"] == 4
    assert result["history"]["comparison_as_of"]["1d"] == "2026-09-17"


def test_repeated_render_of_one_date_does_not_manufacture_acceleration(monkeypatch):
    one_day = snapshot("2026-09-17", 20, 40)
    result = pulse(monkeypatch, [deepcopy(one_day) for _ in range(8)])
    row = result["themes"][0]
    assert row["rank_delta_5d"] is None
    assert row["score_delta_5d"] is None
    assert "leader" not in result["heating"]
    assert result["history"]["comparison_as_of"]["5d"] is None


def test_archive_input_order_does_not_define_the_observation_window(monkeypatch):
    history = [snapshot("2026-09-16", 11), snapshot("2026-09-17", 9),
               snapshot("2026-09-18", 5)]
    assert pulse(monkeypatch, history) == pulse(monkeypatch, list(reversed(history)))


def test_duplicate_date_uses_the_archive_owners_keep_first_law(monkeypatch):
    history = [snapshot("2026-09-17", 9), snapshot("2026-09-17", 30),
               snapshot("2026-09-18", 5)]
    result = pulse(monkeypatch, history)
    assert result["themes"][0]["rank_delta_1d"] == 4


@pytest.mark.parametrize("asof", [None, "", "not-a-date", "2026-02-30", True, 20260918])
def test_unknown_observation_date_is_not_redated_to_build_day(monkeypatch, asof):
    assert pulse(monkeypatch, [], asof=asof) is None


@pytest.mark.parametrize("bad", [None, "broken", {}, {"asof": "garbage"},
                                 snapshot("2026-02-30"), {"asof": "2026-09-17", "themes": []}])
def test_malformed_archive_rows_do_not_displace_a_usable_comparison(monkeypatch, bad):
    result = pulse(monkeypatch, [snapshot("2026-09-17", 9), bad])
    assert result is not None
    assert result["themes"][0]["rank_delta_1d"] == 4


def test_empty_history_remains_unknown_not_zero(monkeypatch):
    result = pulse(monkeypatch, [])
    assert result["themes"][0]["rank_delta_1d"] is None
    assert result["history"]["comparison_as_of"] == {"1d": None, "5d": None, "20d": None}


def test_five_day_comparison_is_dated_and_preserves_a_real_zero_score(monkeypatch):
    dates = ["2026-09-11", "2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17"]
    result = pulse(monkeypatch, [snapshot(day, 9, 0) for day in dates])
    row = result["themes"][0]
    assert row["rank_delta_5d"] == 4
    assert row["score_delta_5d"] == 65
    assert result["history"]["comparison_as_of"]["5d"] == "2026-09-11"
    assert result["history"]["basis"] == "nyse_sessions"


def test_projection_does_not_mutate_sources_or_change_recommendation_authority(monkeypatch):
    history = [snapshot("2026-09-17", 9), snapshot("2026-09-21", 1)]
    before = deepcopy(history)
    result = pulse(monkeypatch, history)
    assert history == before
    row = result["themes"][0]
    assert (row["rank"], row["score"], row["label"], row["reco"]) == (5, 65, "dominant", "hold")
    assert result["as_of"] == "2026-09-18"


@pytest.mark.parametrize("region", ["us", "china", "hk", "canada"])
def test_regions_keep_their_own_observation_clock(monkeypatch, region):
    result = pulse(monkeypatch, [snapshot("2026-09-17", 9)], region=region)
    assert result["region"] == region
    assert result["themes"][0]["rank_delta_1d"] == 4


@pytest.mark.parametrize("region", ["us", "china", "hk", "canada"])
def test_reader_writer_and_theme_enrichment_share_the_same_observation(monkeypatch, tmp_path, region):
    import json

    history = [snapshot("2026-09-16", 11), snapshot("2026-09-17", 9),
               snapshot("2026-09-21", 1)]
    expected = pulse(monkeypatch, history, region=region)
    ti = {"as_of": "2026-09-18", "themes": [theme()]}
    original = deepcopy(ti)
    # The writer must use its fresh producer argument, not a different disk cache.
    monkeypatch.setattr(sp, "_load_theme_intel", lambda _: (_ for _ in ()).throw(AssertionError("disk read")))
    sp.write_pulse(ti, region, tmp_path)
    filename = "sector_pulse.json" if region == "us" else f"sector_pulse_{region}.json"
    assert json.loads((tmp_path / filename).read_text()) == expected
    assert ti == original
    sp.merge_pulse_into_theme_intel(ti, region)
    row = ti["themes"][0]
    assert row["pulse_rank_delta_1d"] == expected["themes"][0]["rank_delta_1d"] == 4
    assert row["pulse_rank_delta_5d"] is expected["themes"][0]["rank_delta_5d"] is None
    assert row["pulse_heat"] == expected["themes"][0]["heat"]
    assert {k: row[k] for k in original["themes"][0]} == original["themes"][0]


@pytest.mark.parametrize("asof", [None, "", "not-a-date"])
def test_unknown_clock_cannot_publish_or_enrich_as_current(monkeypatch, tmp_path, asof):
    monkeypatch.setattr(sp, "_load_archive_snapshots", lambda _: [snapshot("2026-09-17")])
    ti = {"as_of": asof, "themes": [theme()]}
    original = deepcopy(ti)
    existing = tmp_path / "sector_pulse.json"
    existing.write_text('{"as_of":"2026-09-17","previous":"dated evidence"}')
    before = existing.read_bytes()
    sp.write_pulse(ti, "us", tmp_path)
    sp.merge_pulse_into_theme_intel(ti, "us")
    assert existing.read_bytes() == before
    assert ti == original


def test_empty_payload_does_not_create_a_publication(monkeypatch, tmp_path):
    monkeypatch.setattr(sp, "_load_archive_snapshots", lambda _: [])
    sp.write_pulse({"as_of": "2026-09-18", "themes": []}, "us", tmp_path)
    assert not (tmp_path / "sector_pulse.json").exists()


def test_us_archive_gap_does_not_shift_the_five_session_endpoint(monkeypatch):
    history = [snapshot("2026-09-10", 40), snapshot("2026-09-11", 9),
               snapshot("2026-09-14", 12), snapshot("2026-09-16", 10),
               snapshot("2026-09-17", 8)]  # September 15 is missing.
    result = pulse(monkeypatch, history)
    assert result["themes"][0]["rank_delta_5d"] == 4
    assert result["history"]["comparison_as_of"]["5d"] == "2026-09-11"


def test_missing_prior_session_cannot_be_replaced_by_an_older_print(monkeypatch):
    result = pulse(monkeypatch, [snapshot("2026-09-16", 50)])
    assert result["themes"][0]["rank_delta_1d"] is None
    assert result["history"]["comparison_as_of"]["1d"] is None
    assert result["history"]["expected_comparison_as_of"]["1d"] == "2026-09-17"


def test_missing_five_session_endpoint_remains_unknown_despite_older_data(monkeypatch):
    history = [snapshot(day, 30) for day in ["2026-09-08", "2026-09-09", "2026-09-10",
                                           "2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17"]]
    result = pulse(monkeypatch, history)
    assert result["themes"][0]["rank_delta_5d"] is None
    assert result["history"]["expected_comparison_as_of"]["5d"] == "2026-09-11"


def test_us_holiday_print_is_not_a_trading_session(monkeypatch):
    result = pulse(monkeypatch, [snapshot("2026-07-02", 9), snapshot("2026-07-03", 40)],
                   asof="2026-07-06")
    assert result["themes"][0]["rank_delta_1d"] == 4
    assert result["history"]["comparison_as_of"]["1d"] == "2026-07-02"


def test_us_weekend_prints_cannot_push_friday_out_of_mondays_comparison(monkeypatch):
    result = pulse(monkeypatch, [snapshot("2026-09-18", 9), snapshot("2026-09-19", 40),
                                snapshot("2026-09-20", 50)], asof="2026-09-21")
    assert result["themes"][0]["rank_delta_1d"] == 4
    assert result["history"]["comparison_as_of"]["1d"] == "2026-09-18"


def test_non_session_theme_date_does_not_fabricate_us_session_comparisons(monkeypatch):
    result = pulse(monkeypatch, [snapshot("2026-09-18", 9)], asof="2026-09-19")
    assert result["as_of"] == "2026-09-19"
    assert result["themes"][0]["rank_delta_1d"] is None
    assert result["history"]["expected_comparison_as_of"] == {"1d": None, "5d": None, "20d": None}


def test_other_regions_do_not_inherit_the_us_holiday_calendar(monkeypatch):
    result = pulse(monkeypatch, [snapshot("2026-07-03", 9)], asof="2026-07-06", region="hk")
    assert result["themes"][0]["rank_delta_1d"] == 4
    assert result["history"]["basis"] == "distinct_dated_archive_observations"
    assert result["history"]["comparison_as_of"]["1d"] == "2026-07-03"
