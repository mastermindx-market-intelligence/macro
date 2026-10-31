"""Retained owner-preview chronology tests: no live data or new state writer."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta

from engine.sector_theme_owner_bridge import preview_us_theme_packet
from engine.sector_theme_regime_timeline import compose_regime_timeline
from tests.test_sector_theme_owner_bridge import fixture, END, DECISION


def stamp(value: str, days: int) -> str:
    return (datetime.fromisoformat(value) + timedelta(days=days)).isoformat()


def at_offset(days: int, *, returns=(.04, .03), missing=()):
    p = fixture()
    m = p["market"]
    for key in ("period_start", "period_end", "decision_at"):
        m[key] = stamp(m[key], days)
    for obs in [m["benchmark"], m["parent"], *m["member_rows"].values()]:
        for key in ("period_start", "period_end", "observed_at", "available_at"):
            obs[key] = stamp(obs[key], days)
    m["member_rows"]["AAA"]["return_frac"] = returns[0]
    m["member_rows"]["BBB"]["return_frac"] = returns[1]
    for ticker in missing:
        del m["member_rows"][ticker]
    p["membership_asof"]["asof"] = (
        END + timedelta(days=days)).date().isoformat()
    return preview_us_theme_packet(p)


def pair(*, before=(.04, .03), after=(-.04, .03),
         before_missing=(), after_missing=()):
    return (
        at_offset(0, returns=before, missing=before_missing),
        at_offset(1, returns=after, missing=after_missing),
    )


def test_p3b_01_paired_deterioration_has_exact_common_member_flips():
    result = compose_regime_timeline(pair())
    assert result["status"] == "RESEARCH_PREVIEW_ONLY"
    assert result["original_issued_snapshots_authenticated"] is False
    assert result["no_interpolation_or_outcome_access_in_this_composer"] is True
    assert result["absence_of_upstream_lookahead_proven"] is False
    change = result["changes"][0]
    assert change["stable_population"] is True
    assert change["paired_member_positive_return"]["newly_negative_common"] == [
        "SEC_AAA"]
    assert change["paired_member_positive_return"]["newly_positive_common"] == []
    assert change["paired_member_positive_return"][
        "endpoint_only_not_intrawindow_crossing_history"] is True
    assert change["aggregate_positive_breadth_delta"][
        "delta_identification_bounds"] == [-.5, -.5]
    assert change["aggregate_positive_breadth_delta"][
        "direction"] == "narrowing_proven"
    assert result["customer_publication"] is False
    assert result["forecast_authority"] is False


def test_p3b_02_true_common_broadening_with_empty_missingness():
    p = pair(before=(-.04, -.03), after=(.01, .02))
    result = compose_regime_timeline(p)
    change = result["changes"][0]
    assert change["paired_member_positive_return"]["newly_positive_common"] == [
        "SEC_AAA", "SEC_BBB"]
    assert change["aggregate_positive_breadth_delta"]["direction"] == (
        "broadening_proven")
    assert change["aggregate_positive_breadth_delta"][
        "delta_identification_bounds"] == [1.0, 1.0]


def test_p3b_03_coverage_arrival_never_called_common_member_flip():
    result = compose_regime_timeline(pair(
        before_missing=("BBB",), after=(-.03, .03),
    ))
    change = result["changes"][0]
    assert change["paired_member_positive_return"][
        "new_coverage_positive"] == ["SEC_BBB"]
    assert change["paired_member_positive_return"]["newly_negative_common"] == [
        "SEC_AAA"]
    assert change["aggregate_positive_breadth_delta"]["direction"] == (
        "direction_not_identified")
    assert change["aggregate_positive_breadth_delta"][
        "delta_identification_bounds"] == [-.5, 0.0]


def test_p3b_04_rolling_window_rs_change_is_explicitly_not_acceleration():
    result = compose_regime_timeline(pair(
        before=(.01, .02), after=(.05, .04),
    ))
    change = result["changes"][0]["rolling_window_rs_level_change_not_acceleration"]
    assert change["status"] == "measured"
    # Both trailing returns use SPY +1%, so 0.03 nominal change maps to
    # 0.03 / 1.01 in relative-wealth space, not a simple return difference.
    assert abs(change["value"] - (.03 / 1.01)) < 1e-12
    assert change["unit"] == "fraction"
    assert "acceleration" not in result["changes"][0]


def test_p3b_05_one_missing_quote_blocks_full_cohort_rs_but_not_bounds():
    result = compose_regime_timeline(pair(
        before_missing=("BBB",), after_missing=("AAA",),
    ))
    c = result["changes"][0]
    assert c["rolling_window_rs_level_change_not_acceleration"] == {
        "status": "unmeasured", "reason": "incomplete_rs_history",
    }
    assert c["aggregate_positive_breadth_delta"][
        "direction"] == "direction_not_identified"
    assert result["observations"][0]["rs_market"] is None


def test_p3b_06_member_revision_change_blocks_unqualified_comparison():
    previous, latter = pair()
    latter["frame"]["group"]["membership_revision"] = "rev2"
    latter["fingerprint"]["group"]["membership_revision"] = "rev2"
    c = compose_regime_timeline([previous, latter])["changes"][0]
    assert c["stable_population"] is False
    assert c["aggregate_positive_breadth_delta"]["reason"] == (
        "roster_or_membership_revision_changed")
    assert c["paired_member_positive_return"]["status"] == "unmeasured"


def test_p3b_07_current_roster_mode_change_does_not_launder_pit():
    p = fixture()
    p["membership_mode"] = "CURRENT_ROSTER"
    p["membership_asof"].update(pit=False, basis="current_membership",
                                snapshot_date=None)
    p["membership_known_at"] = DECISION.isoformat()
    old = preview_us_theme_packet(p)
    new = at_offset(1)
    result = compose_regime_timeline([old, new])
    assert result["status"] == "RESEARCH_PREVIEW_ONLY"
    assert result["changes"][0]["stable_population"] is False
    assert result["changes"][0]["paired_member_uptrend"]["status"] == "unmeasured"
    assert [row["membership_basis"] for row in result["observations"]] == [
        "CURRENT_ROSTER", "PIT_AS_KNOWN"]


def test_p3b_08_no_mixed_market_benchmark_or_session_basis():
    p = at_offset(1)
    p["comparison_basis"]["benchmark_id"] = "QQQ"
    result = compose_regime_timeline([at_offset(0), p])
    assert result["reason"] == "different_group_or_incompatible_basis"
    p = at_offset(1)
    p["comparison_basis"]["session_basis"] = "overnight"
    assert compose_regime_timeline([at_offset(0), p])["status"] == "HELD"


def test_p3b_09_reverse_and_duplicate_cutoffs_are_rejected():
    p = pair()
    assert compose_regime_timeline(p[::-1])["reason"] == (
        "nonmonotonic_source_snapshot_order")
    assert compose_regime_timeline((p[0], p[0]))["reason"] == (
        "nonmonotonic_source_snapshot_order")


def test_p3b_10_same_group_identity_required_for_retained_snapshots():
    p = list(pair())
    p[1]["frame"]["group"]["group_id"] = "ANOTHER"
    p[1]["fingerprint"]["group"]["group_id"] = "ANOTHER"
    assert compose_regime_timeline(p)["reason"] == (
        "different_group_or_incompatible_basis")


def test_p3b_11_historical_accuracy_not_inferred_from_source_shape():
    a, b = pair()
    b["fingerprint"]["authority"]["predictive_promoted"] = True
    out = compose_regime_timeline([a, b])
    assert out["reason"] == "fingerprint_claims_authority"
    b = pair()[1]
    b["eligible_for_historical_prediction"] = True
    assert compose_regime_timeline([a, b])["reason"] == (
        "unqualified_or_modified_source_preview")


def test_p3b_12_invalid_breadth_bounds_do_not_become_false_direction():
    a, b = pair()
    b["fingerprint"]["horizons"]["5d"]["participation"][
        "positive_return_breadth"]["identification_bounds"] = [1.8, 1.9]
    result = compose_regime_timeline([a, b])
    # A fingerprint with corrupted coverage bounds is not the source frame.
    # Refuse the whole chronology rather than displaying a suspect direction.
    assert result["status"] == "HELD"
    assert result["reason"] == "fingerprint_frame_numeric_mismatch"
    assert result["changes"] == []
    assert result["ranking_or_trading_authority"] is False


def test_p3b_13_future_unknown_clock_or_broken_end_is_held():
    a, b = pair()
    b["comparison_basis"]["decision_at"] = "2030-01-01"
    assert compose_regime_timeline([a, b])["reason"] == "invalid_source_clock"
    b = pair()[1]
    b["comparison_basis"]["period_start"] = b["comparison_basis"]["period_end"]
    assert compose_regime_timeline([a, b])["reason"] == "invalid_source_clock"


def test_p3b_14_retains_three_observed_snapshots_and_two_paired_changes():
    p = [at_offset(0), at_offset(1), at_offset(2)]
    result = compose_regime_timeline(p)
    assert result["status"] == "RESEARCH_PREVIEW_ONLY"
    assert len(result["observations"]) == 3
    assert len(result["changes"]) == 2
    assert result["observations"][2]["period_end"] == stamp(END.isoformat(), 2)


def test_p3b_15_no_mutation_or_unregistered_external_consumer():
    packets = list(pair())
    before = deepcopy(packets)
    first = compose_regime_timeline(packets)
    second = compose_regime_timeline(packets)
    assert packets == before and first == second
    assert first["ranking_or_trading_authority"] is False


def test_p3b_16_requires_at_least_two_valid_source_previews():
    assert compose_regime_timeline([])["reason"] == "need_two_source_previews"
    assert compose_regime_timeline([at_offset(0)])["reason"] == (
        "need_two_source_previews")
    assert compose_regime_timeline([None, at_offset(1)])["reason"] == (
        "unqualified_or_modified_source_preview")


def test_p3b_17_malformed_evidence_or_member_state_is_held_without_exception():
    a, b = pair()
    b["frame"]["evidence"] = None
    assert compose_regime_timeline([a, b])["reason"] == (
        "missing_constituent_observation")
    b = pair()[1]
    b["frame"]["constituents"]["SEC_AAA"] = "bad"
    assert compose_regime_timeline([a, b])["reason"] == (
        "malformed_constituent_state")
    b = pair()[1]
    b["frame"]["constituents"].pop("SEC_BBB")
    assert compose_regime_timeline([a, b])["reason"] == (
        "invalid_source_population")


def test_p3b_recovery_switching_parent_invalidates_rs_history():
    rows = list(pair())
    rows[1]["comparison_basis"]["parent_id"] = "XLP"
    result = compose_regime_timeline(rows)
    assert result["status"] == "HELD"
    assert result["reason"] == "different_group_or_incompatible_basis"
    good = compose_regime_timeline(pair())
    assert good["status"] == "RESEARCH_PREVIEW_ONLY"
    assert good["time_basis"]["parent_id"] == "XLK"
    assert all(obs["parent_id"] == "XLK" for obs in good["observations"])


def test_p3b_recovery_caller_forged_population_counts_fail_closed():
    for corruption, expected in (
        (("unique_issuer_n", "many"), "invalid_unique_issuer_population"),
        (("measured_return_n", 99), "invalid_measured_security_count"),
    ):
        field, forged = corruption
        rows = list(pair())
        if field == "measured_return_n":
            rows[1]["frame"]["universe"][field] = forged
        else:
            rows[1][field] = forged
        result = compose_regime_timeline(rows)
        assert result["status"] == "HELD"
        assert result["reason"] == expected


def test_p3b_recovery_forged_security_issuer_map_fails_closed():
    rows = list(pair())
    rows[1]["issuer_by_security_id"]["SEC_BBB"] = {}
    result = compose_regime_timeline(rows)
    assert result["status"] == "HELD"
    assert result["reason"] == "missing_or_invalid_security_issuer_mapping"


def test_p3b_recovery_fp_members_must_match_frame():
    rows = list(pair())
    rows[1]["fingerprint"]["group"]["member_ids"] = ["SEC_AAA", "FAKE"]
    assert compose_regime_timeline(rows)["reason"] == "invalid_source_population"


def test_p3b_recovery_noncausal_membership_known_at_refused():
    rows = list(pair())
    rows[1]["frame"]["clock"]["membership_known_at"] = (
        "2026-11-10T20:00:00+00:00")
    assert compose_regime_timeline(rows)["reason"] == "noncausal_membership_availability"


def test_p3b_recovery_fp_numeric_must_be_recomputed_from_source_frame():
    rows = list(pair())
    rows[0]["fingerprint"]["horizons"]["5d"]["rs_market"] = {
        "status": "measured", "unit": "fraction", "value": -0.90,
    }
    result = compose_regime_timeline(rows)
    assert result["status"] == "HELD"
    assert result["reason"] == "fingerprint_frame_numeric_mismatch"


def test_p3b_recovery_measured_n_matches_constituent_return_states():
    rows = list(pair())
    rows[0]["frame"]["universe"]["measured_return_n"] = 0
    result = compose_regime_timeline(rows)
    assert result["status"] == "HELD"
    assert result["reason"] == "invalid_measured_security_count"


def test_p3b_recovery_no_theme_parent_even_if_every_row_omits_it():
    rows = list(pair())
    for r in rows:
        r["comparison_basis"]["parent_id"] = None
    result = compose_regime_timeline(rows)
    assert result["status"] == "HELD"
    assert result["reason"] == "missing_theme_parent_identity"


def test_p3b_recovery_unknown_group_kind_refused():
    rows = list(pair())
    rows[1]["group_kind"] = "microtheme_without_native_members"
    result = compose_regime_timeline(rows)
    assert result["status"] == "HELD"
    assert result["reason"] == "unqualified_group_kind"
