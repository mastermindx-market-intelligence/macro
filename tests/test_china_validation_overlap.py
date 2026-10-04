"""Overlap-awareness of the China cross-sectional validator (engine/china_validation).

The fundflow/chips stores were designed as a WEEKLY grid but accreted to a DAILY one (the
tail-anchored stride in collectors/tushare_history._grid_dates phase-shifts every build). Daily
cross-sections against multi-day forward returns overlap heavily, so a row count is not a sample
size and a HAC lag sized for a weekly step is far too short. These tests pin the three properties
that keep the `proven` verdict honest under ANY cadence:

  1. the honest counts (distinct weeks, non-overlapping forward windows) are cadence-INVARIANT —
     a daily and a weekly grid over the same span report the same evidence, though `n` differs 5x;
  2. the HAC truncation lag is measured from the grid, not assumed;
  3. the promotion gate reads the honest counts, so no family reaches "proven" on overlap alone.

Pure pandas/numpy — no network, no token, no data/ reads.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import engine.validation as V
from engine import china_validation as cv


# --------------------------------------------------------------------------- #
# synthetic panel (deterministic)
# --------------------------------------------------------------------------- #
def _panel_and_bench(n_days: int = 320, n_names: int = 15):
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2024-01-01", periods=n_days)
    px = pd.DataFrame(
        100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, size=(n_days, n_names)), axis=0)),
        index=idx, columns=[f"{600000 + i}.SS" for i in range(n_names)])
    bench = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.008, n_days))), index=idx)
    return px, bench


def _cross_sections(panel, step: int, stop: int = 280):
    """{asof: Series(ticker->signal)} sampled every `step` trading days."""
    rng = np.random.default_rng(11)
    return {d: pd.Series(rng.normal(size=len(panel.columns)), index=panel.columns)
            for d in panel.index[:stop:step]}


# --------------------------------------------------------------------------- #
# 1. cadence forensics
# --------------------------------------------------------------------------- #
def test_sampling_step_detects_daily_vs_weekly():
    panel, _ = _panel_and_bench()
    daily = cv._cal_positions(list(panel.index[:200]), panel.index)
    weekly = cv._cal_positions(list(panel.index[:200:5]), panel.index)
    assert cv._sampling_step(daily) == 1.0
    assert cv._sampling_step(weekly) == 5.0
    # unknowable cadence must fail CONSERVATIVE — a short step buys more HAC lags, never fewer
    assert cv._sampling_step([]) == 1.0 and cv._sampling_step([3]) == 1.0


def test_hac_lags_track_the_measured_overlap():
    # weekly step: a 21d window spans ~4.2 steps → 5 lags (≈ the hard-coded 6 the harness used,
    # which is exactly why the old constant looked correct under the original design)
    assert cv._hac_lags_for(21, 5.0) == 5
    # daily step: the SAME horizon now spans 21 steps — 6 lags would truncate ~3x too early
    assert cv._hac_lags_for(21, 1.0) == 21
    assert cv._hac_lags_for(63, 1.0) == 63
    assert cv._hac_lags_for(5, 5.0) == 1                 # non-overlapping → minimum lag
    assert cv._hac_lags_for(21, 0.0) >= 1                # degenerate step never divides by zero


def test_disjoint_windows_counts_non_overlapping_only():
    # 100 consecutive daily observations, 21-day forward window → ceil(100/21) = 5 disjoint
    assert cv._disjoint_windows(list(range(100)), 21) == 5
    assert cv._disjoint_windows(list(range(100)), 1) == 100      # no overlap → every row counts
    assert cv._disjoint_windows([0, 30, 60], 21) == 3            # already disjoint
    assert cv._disjoint_windows([0, 1, 2], 21) == 1              # all inside one window
    assert cv._disjoint_windows([], 21) == 0


def test_distinct_weeks_is_cadence_invariant():
    idx = pd.bdate_range("2024-01-01", periods=100)
    # 100 daily dates and the 20 weekly dates spanning them cover the SAME calendar weeks
    assert cv._distinct_weeks(list(idx)) == cv._distinct_weeks(list(idx[::5])) == 20
    assert cv._distinct_weeks([]) == 0


# --------------------------------------------------------------------------- #
# 2. the crux: a daily grid must not report more EVIDENCE than a weekly one
# --------------------------------------------------------------------------- #
def test_daily_grid_reports_same_honest_n_as_weekly_over_same_span():
    """The regression this module exists for. Over one identical span, a daily grid scores ~5x
    the rows of a weekly grid — but the same weeks, and independent-window counts that differ by
    a tiling remainder rather than by the sampling ratio. `n` inflates; the evidence does not."""
    panel, bench = _panel_and_bench()
    daily = cv._validate_xs(V, "fundflow", _cross_sections(panel, 1),
                            panel, bench, (21,), neutralize=False)
    weekly = cv._validate_xs(V, "fundflow", _cross_sections(panel, 5),
                             panel, bench, (21,), neutralize=False)
    d, w = daily["by_horizon"]["21"], weekly["by_horizon"]["21"]

    assert d["sampling_step_td"] == 1.0 and w["sampling_step_td"] == 5.0
    assert d["n"] > 4 * w["n"]                       # rows inflate ~5x with the finer grid...
    assert d["n_weeks"] == w["n_weeks"]              # ...but the calendar span is identical
    # ...and the independent evidence barely moves. The daily grid tiles 21d windows exactly
    # while the weekly one can only start them on 5d boundaries (25d apart), so it packs a few
    # fewer — a remainder effect, NOT the 5x the row count claims.
    assert w["n_indep"] <= d["n_indep"] <= w["n_indep"] * 1.3
    assert d["n_indep"] < d["n"] / 15                # 21d windows over a daily grid: ~21x fewer

    # the lag follows the cadence, so both grids Bartlett-weight the same real overlap
    assert d["hac_lags"] == 21 and w["hac_lags"] == 5
    assert d["overlap_ratio"] == 21.0 and w["overlap_ratio"] == 4.2


def test_honest_counts_present_on_every_horizon_block():
    """'Print the honest N either way' — the counts are reported whether or not they gate."""
    panel, bench = _panel_and_bench()
    fam = cv._validate_xs(V, "fundflow", _cross_sections(panel, 1),
                          panel, bench, (5, 21, 63), neutralize=False)
    for h, block in fam["by_horizon"].items():
        for key in ("n", "n_weeks", "n_indep", "sampling_step_td", "hac_lags", "overlap_ratio"):
            assert block.get(key) is not None, f"h={h} missing {key}"
    # longer horizon over a fixed span ⇒ strictly less independent evidence
    b = fam["by_horizon"]
    assert b["5"]["n_indep"] > b["21"]["n_indep"] > b["63"]["n_indep"]


def test_hac_lag_override_raises_the_se_on_an_overlapping_series():
    """The primitive-level fix: honouring the real overlap widens the HAC se, lowering t."""
    rng = np.random.default_rng(3)
    # MA(21)-ish series: exactly the autocorrelation an overlapping forward window injects
    overlapping = pd.Series(np.convolve(rng.normal(0.04, 1.0, 600), np.ones(21) / 21, "same"))
    short = V.ic_summary(overlapping, periods_per_year=12)                 # legacy: 6 lags
    honest = V.ic_summary(overlapping, periods_per_year=12, hac_lags=21)   # measured overlap
    assert short["hac_lags"] == 6 and honest["hac_lags"] == 21
    assert abs(honest["t_hac"]) < abs(short["t_hac"])       # under-lagging inflated t
    assert honest["mean_ic"] == short["mean_ic"]            # the ESTIMATE is untouched


def test_ic_summary_default_lag_unchanged():
    """The hac_lags kwarg is additive — every existing caller keeps its old numbers."""
    rng = np.random.default_rng(5)
    ics = pd.Series(rng.normal(0.03, 0.08, 40))
    assert V.ic_summary(ics, periods_per_year=12)["t_hac"] == \
        V.ic_summary(ics, periods_per_year=12, hac_lags=None)["t_hac"]
    assert V.ic_summary(ics, periods_per_year=4)["hac_lags"] == 2


def test_ic_summary_coerces_non_int_lags_rather_than_silently_shortening():
    """A numpy int or a 21.0 float must be honoured. Silently falling back to the shorter
    default would reintroduce exactly the anticonservative t this override exists to fix."""
    rng = np.random.default_rng(5)
    ics = pd.Series(rng.normal(0.03, 0.08, 40))
    assert V.ic_summary(ics, periods_per_year=12, hac_lags=np.int64(9))["hac_lags"] == 9
    assert V.ic_summary(ics, periods_per_year=12, hac_lags=9.0)["hac_lags"] == 9
    # unusable values fall back to the documented default rather than crashing a build
    assert V.ic_summary(ics, periods_per_year=12, hac_lags="nope")["hac_lags"] == 6
    assert V.ic_summary(ics, periods_per_year=12, hac_lags=0)["hac_lags"] == 6


# --------------------------------------------------------------------------- #
# 3. the promotion gate reads the honest counts
# --------------------------------------------------------------------------- #
def _head(n_weeks, n_indep, t=3.0, ic=0.05, n=272):
    return {"21": {"mean_ic": ic, "t_hac": t, "p_hac": 0.001, "hit": 0.6,
                   "n": n, "n_weeks": n_weeks, "n_indep": n_indep}}


def test_proven_requires_non_overlapping_windows_not_rows():
    """272 overlapping rows and a t of 3.0 must NOT promote on 3 independent windows — the
    h=63 shape on the live store (fundflow t 3.075 there, on 3 disjoint windows)."""
    blocked = cv._finalize("fundflow", _head(n_weeks=60, n_indep=3), 272, cv._MIN_PROVEN_N)
    assert blocked["proven"] is False
    assert blocked["n_indep"] == 3 and blocked["n_obs"] == 272
    assert "non-overlapping" in blocked["n_gate"]        # says WHICH count fell short

    ok = cv._finalize("fundflow", _head(n_weeks=60, n_indep=12), 272, cv._MIN_PROVEN_N)
    assert ok["proven"] is True and "n_gate" not in ok


def test_proven_requires_distinct_weeks_not_scored_rows():
    """A dense grid over a SHORT span: 272 rows clears the old n>=40 gate; 9 weeks must not."""
    thin = cv._finalize("guidance", _head(n_weeks=9, n_indep=12), 272, cv._MIN_PROVEN_N)
    assert thin["proven"] is False and thin["n_weeks"] == 9
    assert "weeks" in thin["n_gate"]


def test_weekly_design_still_reaches_proven():
    """No goalpost move: the ORIGINAL weekly grid (52 cross-sections = 52 weeks, 12 disjoint
    21d windows) clears the gate exactly as it always did."""
    weekly = cv._finalize("fundflow", _head(n_weeks=52, n_indep=12, n=52), 52, cv._MIN_PROVEN_N)
    assert weekly["proven"] is True and weekly["status"] == "scored"


def test_wrong_sign_still_blocks_promotion():
    """The sign gate is untouched — honest N never rescues a wrong-sign family."""
    wrong = cv._finalize("chips", _head(n_weeks=60, n_indep=12, ic=0.05), 272, cv._MIN_PROVEN_N)
    assert wrong["sign_ok"] is False and wrong["proven"] is False   # chips expects ic < 0


def test_n_obs_stays_nominal_for_the_demotion_path():
    """china_signal_lab zeroes a wrong-sign leg on `n_obs >= _MIN_PROVEN_N_TS`. Demotion carries
    the lighter burden by design, so the raw row count must survive the honest-N change."""
    fam = cv._finalize("fundflow", _head(n_weeks=60, n_indep=3), 272, cv._MIN_PROVEN_N)
    assert fam["n_obs"] == 272                       # NOT shrunk to the honest count
    assert fam["n_weeks"] == 60 and fam["n_indep"] == 3

# --------------------------------------------------------------------------- #
# 4. CIE-18 pre-outcome preregistration admission
# --------------------------------------------------------------------------- #

def _cie18_prereg(track="D"):
    base = {
        "schema": cv.CIE18_PREREG_SCHEMA,
        "experiment_id": f"cie18-{track.lower()}-001",
        "version": 1,
        "track": track,
        "mechanism": "frozen owner-native evidence treatment",
        "role": "discovery" if track == "D" else "ordering" if track == "O" else "monitoring",
        "sign_prior": "none_declared",
        "horizon": 21,
        "horizon_unit": "trading_sessions",
        "falsifier": "no incremental decision value under the frozen comparison",
        "source_owner_refs": ["WS:CHINA-ALPHA-INTELLIGENCE", "DataOS:china"],
        "source_use_permissions": {"class": "approved_internal_research"},
        "population_manifest": {"asof_rule": "historical eligible universe at cutoff"},
        "availability_contract": {
            "cutoff": "evidence_available_at<=decision_cutoff",
            "later_corrections": "new_revision_only",
        },
        "outcome_contract": {
            "benchmark": "510300.SS",
            "fill_basis": "canonical_owner",
            "correction_policy": "frozen_by_version",
        },
        "development_interval": {"start": "2025-01-01", "end": "2025-06-30"},
        "holdout_interval": {"start": "2025-07-01", "end": "2025-12-31"},
        "prospective_contract": {
            "start": "2026-01-01",
            "end_rule": "until preregistered independent-N or calendar stop, whichever comes first",
        },
        "primary_metric": {
            "name": "decision_value",
            "definition": "frozen track-specific primary economic or decision metric",
            "direction": "higher_is_better",
        },
        "minimum_useful_effect": 0.01,
        "downside_bound": 0.02,
        "multiplicity": {
            "confirmation_method": "holm_fwer",
            "confirmation_alpha": 0.05,
            "confirmation_family": ["primary", "registered_secondary"],
            "exploratory_method": "bh_fdr",
        },
        "clustering": {"unit": "issuer_event_date", "effective_n_reported": True},
        "power": {"basis": "development_only", "minimum_independent_n": 40},
        "stopping_rule": {
            "mode": "fixed_no_interim_inference",
            "final_read_rule": "one final confirmation read after accrual gate",
        },
        "trial_family": f"cie18_{track.lower()}_family",
        "declared_trial_budget": 12,
        "attempted_variants": [{"name": "primary", "horizon": 21}],
        "negative_controls": [{"name": "time_shift"}, {"name": "scrambled_identity"}],
        "cost_capacity_contract": {"slippage": "conservative", "capacity": "reported"},
        "source_reliability_contract": {"unavailable": "exclude_with_reason"},
        "code_sha": "a" * 40,
        "input_hashes": {"manifest": "b" * 64, "feature_contract": "c" * 64},
        "outcome_access_state": "SEALED_UNSEEN",
    }
    if track == "D":
        base.update({
            "lawful_asof_universe": {"manifest": "universe-v1"},
            "equal_budget_control": {"policy": "current_discovery", "budget": 100},
            "lead_time_clock": "EVIDENCE_AVAILABLE_AT",
            "future_admission_is_endpoint_only": True,
            "resource_budget": {"names_reviewed": 100},
        })
    elif track == "O":
        base.update({
            "candidate_snapshot_manifest": {"digest": "d" * 64},
            "actual_serving_policy": {"version": "serving-v1"},
            "fallback_state": {"mode": "explicit", "coverage_complete": True},
            "deterministic_tiebreak": {"version": "tie-v1"},
            "original_fill_owner": {"owner": "china_standout_track"},
            "population_identity_rule": "EXACT_SAME_CANDIDATES_AND_TIME",
        })
    elif track == "M":
        base.update({
            "thesis_falsifier_version": "thesis-v1",
            "alert_policy": {"version": "alert-v1", "dedup": "position+thesis+revision"},
            "observability_rule": {"missing_coverage": "UNKNOWN"},
            "action_rule": {"automatic_trade": False, "response": "request_review"},
            "adjudication_policy": {"mode": "blinded_factual_deterioration"},
            "alert_budget": {"max_reviews_per_week": 20},
        })
    return base


def test_cie18_all_three_tracks_admit_only_when_fully_frozen():
    for track in ("D", "O", "M"):
        record = _cie18_prereg(track)
        receipt = cv.validate_cie18_prereg(record)
        assert receipt["admitted_for_outcome_read"] is True, (track, receipt)
        assert receipt["validation_errors"] == []
        assert receipt["prereg_digest"] == cv.cie18_prereg_digest(record)
        assert len(receipt["prereg_digest"]) == 64


def test_cie18_missing_practical_thresholds_is_accrual_gated():
    record = _cie18_prereg("O")
    record["minimum_useful_effect"] = None
    record["downside_bound"] = float("nan")
    receipt = cv.validate_cie18_prereg(record)
    assert receipt["admitted_for_outcome_read"] is False
    assert receipt["disposition_if_incomplete"] == "ACCRUAL_GATED"
    assert "minimum_useful_effect_must_be_positive_finite" in receipt["validation_errors"]
    assert "downside_bound_must_be_nonnegative_finite" in receipt["validation_errors"]
    assert receipt["prereg_digest"] is None


def test_cie18_refuses_viewed_results_and_result_fields():
    record = _cie18_prereg("D")
    record["outcome_access_state"] = "HOLDOUT_VIEWED"
    record["point_estimates"] = {"primary": 0.12}
    receipt = cv.validate_cie18_prereg(record)
    assert receipt["admitted_for_outcome_read"] is False
    assert "outcome_access_state_must_be_SEALED_UNSEEN" in receipt["validation_errors"]
    assert "outcome_field_forbidden:point_estimates" in receipt["validation_errors"]


def test_cie18_refuses_development_holdout_overlap():
    record = _cie18_prereg("D")
    record["development_interval"]["end"] = "2025-07-15"
    receipt = cv.validate_cie18_prereg(record)
    assert receipt["admitted_for_outcome_read"] is False
    assert "development_holdout_overlap" in receipt["validation_errors"]


def test_cie18_track_o_requires_identical_candidate_population_and_explicit_fallback():
    record = _cie18_prereg("O")
    record["population_identity_rule"] = "roughly_same_candidates"
    record["fallback_state"] = "v4"
    receipt = cv.validate_cie18_prereg(record)
    assert receipt["admitted_for_outcome_read"] is False
    assert "track_O_population_identity_rule_invalid" in receipt["validation_errors"]
    assert "track_O_fallback_state_must_be_explicit" in receipt["validation_errors"]


def test_cie18_track_d_lead_time_is_evidence_availability_not_event_date():
    record = _cie18_prereg("D")
    record["lead_time_clock"] = "EVENT_START_DATE"
    record["future_admission_is_endpoint_only"] = False
    receipt = cv.validate_cie18_prereg(record)
    assert receipt["admitted_for_outcome_read"] is False
    assert "track_D_lead_time_clock_must_be_evidence_available" in receipt["validation_errors"]
    assert "track_D_future_admission_must_be_endpoint_only" in receipt["validation_errors"]


def test_cie18_track_m_cannot_smuggle_automatic_trade_authority():
    record = _cie18_prereg("M")
    record["action_rule"]["automatic_trade"] = True
    receipt = cv.validate_cie18_prereg(record)
    assert receipt["admitted_for_outcome_read"] is False
    assert "track_M_automatic_trade_must_be_false_without_separate_authority" in receipt["validation_errors"]


def test_cie18_confirmation_fdr_is_not_accepted_as_confirmation_family_control():
    record = _cie18_prereg("D")
    record["multiplicity"]["confirmation_method"] = "bh_fdr"
    receipt = cv.validate_cie18_prereg(record)
    assert receipt["admitted_for_outcome_read"] is False
    assert "multiplicity_contract_invalid" in receipt["validation_errors"]


def test_cie18_requires_positive_integer_declared_trial_budget():
    for bad in (0, -1, True, 2.5, "12"):
        record = _cie18_prereg("D")
        record["declared_trial_budget"] = bad
        receipt = cv.validate_cie18_prereg(record)
        assert receipt["admitted_for_outcome_read"] is False
        assert "declared_trial_budget_must_be_positive_int" in receipt["validation_errors"]


def test_cie18_registers_budget_through_existing_trial_ledger_only(tmp_path):
    from engine.trial_ledger import TrialLedger

    record = _cie18_prereg("D")
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    receipt = cv.register_cie18_trial_budget(record, ledger)
    assert receipt["trial_budget_registered"] is True
    assert receipt["trial_budget_observed"] == record["declared_trial_budget"]
    assert ledger.declared_budget(record["trial_family"]) == record["declared_trial_budget"]

    # A lower second declaration cannot reduce the already-accounted research budget.
    record2 = dict(record)
    record2["version"] = 2
    record2["declared_trial_budget"] = 3
    receipt2 = cv.register_cie18_trial_budget(record2, ledger)
    assert receipt2["trial_budget_observed"] == 12


def test_cie18_rejects_missing_canonical_trial_ledger():
    record = _cie18_prereg("D")
    try:
        cv.register_cie18_trial_budget(record, None)
    except ValueError as exc:
        assert "TrialLedger" in str(exc)
    else:
        raise AssertionError("expected missing canonical TrialLedger to fail")


def test_cie18_digest_changes_on_semantic_prereg_change():
    a = _cie18_prereg("D")
    b = _cie18_prereg("D")
    b["minimum_useful_effect"] = 0.02
    assert cv.cie18_prereg_digest(a) != cv.cie18_prereg_digest(b)

