"""Adversarial arithmetic/contract checks using SYNTHETIC, NOT-ENROLLED data.

No fixture is a market observation or an activation receipt. In particular,
calendar dates below are synthetic ordered keys, not an exchange calendar.
The resampling goldens were derived independently using integer arithmetic
series sums around the circular boundary and manual order-statistic linear
interpolation, without the implementation's indexed-array aggregation.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
import json
import math
import unittest

from engine.pb_d_evaluation import (
    BOOTSTRAP_DRAWS,
    EvaluationContext,
    FrozenPair,
    OHLCBar,
    OmissionSensitivity,
    Outcome,
    SECONDARY_ENDPOINTS,
    centered_bootstrap_p_value,
    circular_block_bootstrap,
    compute_ohlc_path,
    evaluate_pb_d,
    holm_adjust,
)


SYNTHETIC_DATES = tuple((date(2020, 1, 1) + timedelta(days=i)).isoformat() for i in range(252))


def context(**changes):
    return EvaluationContext(cohort_id="SYNTHETIC-NOT-ENROLLED", session_dates=SYNTHETIC_DATES, **changes)


def pair(index, session=0, treated=3.0, control=1.0, **changes):
    q1 = Outcome(f"SYNTHETIC-Q1-{index}", f"SYNTHETIC-T-{index}", h5_spy_excess_pp=treated,
                 h10_spy_excess_pp=4.0, h21_spy_excess_pp=2.0, h5_clean_liftoff=True,
                 entry_status="FILLED")
    q0 = Outcome(f"SYNTHETIC-Q0-{index}", f"SYNTHETIC-C-{index}", h5_spy_excess_pp=control,
                 h10_spy_excess_pp=1.0, h21_spy_excess_pp=1.0, h5_clean_liftoff=False,
                 entry_status="FILLED")
    return replace(FrozenPair(f"SYNTHETIC-PAIR-{index}", session, q1, q0, "SYNTHETIC-SECTOR"), **changes)


def bulk_pairs(count=200, active_dates=50):
    return tuple(pair(i, (i % active_dates) * 5) for i in range(count))


class TestFrozenBootstrap(unittest.TestCase):
    def test_circular_arithmetic_series_goldens_and_restart_per_length(self):
        # Effects are the integers 0..251. A block sum is an arithmetic
        # progression before wrapping plus 0..k after wrapping. This pins
        # uniform starts, draw/block order, L=10 truncation, and linear tails.
        expected = {
            21: (86.41666666666667, 116.75, 88.91458333333334, 163.5),
            10: (110.81746031746032, 158.62698412698413, 99.11825396825397, 152.69107142857143),
            42: (80.66666666666667, 132.16666666666666, 77.0, 172.83749999999995),
        }
        first_21 = None
        for length, golden in expected.items():
            result = circular_block_bootstrap(tuple(range(252)), block_length=length)
            self.assertEqual(result.estimate_pp, 125.5)
            self.assertEqual(result.valid_draw_count, 10000)
            self.assertEqual(len(result.replicates), BOOTSTRAP_DRAWS)
            self.assertTrue(result.inference_valid)
            for actual, expected_value in zip((result.replicates[0], result.replicates[-1], *result.interval_pp), golden):
                self.assertAlmostEqual(actual, expected_value, places=11)
            if length == 21:
                first_21 = result
        self.assertEqual(circular_block_bootstrap(tuple(range(252)), block_length=21), first_21)

    def test_inactive_dates_are_never_zero_and_invalid_draw_gate_is_exact(self):
        vector = (None,) * 251 + (7.0,)
        for length, valid_count in ((21, 6475), (10, 6405), (42, 6667)):
            result = circular_block_bootstrap(vector, block_length=length)
            self.assertEqual(result.valid_draw_count, valid_count)
            self.assertEqual(result.no_active_date_draw_count, 10000 - valid_count)
            self.assertEqual(result.estimate_pp, 7.0)
            self.assertEqual(result.interval_pp, (7.0, 7.0))
            self.assertFalse(result.inference_valid)
            self.assertEqual({value for value in result.replicates if value is not None}, {7.0})

    def test_no_active_dates_are_unknown_not_zero(self):
        result = circular_block_bootstrap((None,) * 252)
        self.assertIsNone(result.estimate_pp)
        self.assertIsNone(result.interval_pp)
        self.assertEqual(result.valid_draw_count, 0)
        self.assertEqual(result.no_active_date_draw_count, 10000)
        self.assertFalse(result.inference_valid)
        self.assertEqual(set(result.replicates), {None})

    def test_frozen_calendar_length_block_lengths_and_finite_values(self):
        for vector in ((0.0,) * 251, (0.0,) * 253):
            with self.assertRaises(ValueError):
                circular_block_bootstrap(vector)
        for value in (math.nan, math.inf, -math.inf, True):
            with self.assertRaises(ValueError):
                circular_block_bootstrap((0.0,) * 251 + (value,))
        with self.assertRaises(ValueError):
            circular_block_bootstrap((0.0,) * 252, block_length=20)

    def test_centered_formula_uses_absolute_deviation_and_plus_one(self):
        # theta=2; deviations of [1,2,3,4,5] are [1,0,1,2,3]. Two of five
        # exceed or equal |theta|; (1+2)/(1+5) = 1/2. None is not a draw.
        self.assertEqual(centered_bootstrap_p_value(2, (1, 2, 3, 4, 5, None)), 0.5)
        self.assertEqual(centered_bootstrap_p_value(-2, (-1, -2, -3, -4, -5)), 0.5)
        self.assertEqual(centered_bootstrap_p_value(0, (-2, 0, 2)), 1.0)
        with self.assertRaises(ValueError):
            centered_bootstrap_p_value(2, (None,))

    def test_holm_retains_four_tests_and_enforces_step_down_monotonicity(self):
        self.assertEqual(holm_adjust((0.01, 0.04, 0.03, 1.0)), (0.04, 0.09, 0.09, 1.0))
        self.assertEqual(holm_adjust((0.01, 0.01, 0.04, 0.2)), (0.04, 0.04, 0.08, 0.2))
        self.assertEqual(holm_adjust((1, 1, 1, 1)), (1, 1, 1, 1))
        for values in ((0.01, 0.03, 1.0), (0.01, 0.03, 1.0, 1.1)):
            with self.assertRaises(ValueError):
                holm_adjust(values)


class TestPairAndGateContracts(unittest.TestCase):
    def test_equal_date_weighting_and_whole_pair_omission(self):
        pairs = (pair(0, 0, 10, 0), pair(1, 0, 20, 10), pair(2, 1, 0, 5), pair(3, 2, 100, None))
        report = evaluate_pb_d(pairs, context())
        primary = report["primary"]
        # Date 0 has two +10 pp differences; date 1 has -5 pp. Equal dates
        # give (10-5)/2=2.5, while equal pairs give (10+10-5)/3=5.
        self.assertEqual(primary["equal_date_mean_increment_pp"], 2.5)
        self.assertEqual(primary["equal_pair_mean_increment_pp"], 5.0)
        self.assertEqual(primary["original_pair_count"], 4)
        self.assertEqual(primary["complete_pair_count"], 3)
        self.assertEqual(primary["active_date_count"], 2)
        self.assertEqual(primary["endpoint_completeness"], 0.75)
        self.assertEqual(primary["date_effects_pp"][:3], (10.0, -5.0, None))
        self.assertIsNone(pairs[3].q0.h5_spy_excess_pp)
        self.assertEqual(report["status"], "NOT_ENROLLED")
        self.assertIsNone(report["preregistered_classification"])
        self.assertFalse(report["automatic_promotion"])
        json.dumps(report, allow_nan=False)

    def test_zero_is_not_a_positive_hit_and_unknown_clean_labels_omit_whole_pair(self):
        a, b = pair(0, 0, 0, -1), pair(1, 1, 1, 0)
        b = replace(b, q0=replace(b.q0, h5_clean_liftoff=None))
        report = evaluate_pb_d((a, b), context())
        hit = report["secondary"][SECONDARY_ENDPOINTS[0]]
        clean = report["secondary"][SECONDARY_ENDPOINTS[3]]
        self.assertEqual(hit["equal_date_mean_increment_pp"], 50.0)
        self.assertEqual(clean["complete_pair_count"], 1)
        self.assertEqual(clean["equal_date_mean_increment_pp"], 100.0)
        self.assertEqual(clean["endpoint_completeness"], 0.5)

    def test_fixed_secondary_gates_and_no_synthetic_inferential_claim(self):
        report = evaluate_pb_d(bulk_pairs(), context(first_t2_count=400,
                                                     complete_primary_exposure_count=400, eligible_q1_count=200))
        self.assertEqual(tuple(report["secondary"]), SECONDARY_ENDPOINTS)
        for result in report["secondary"].values():
            self.assertTrue(result["numerical_endpoint_gates_passed"])
            self.assertFalse(result["test_eligible"])
            self.assertTrue(result["descriptive_only"])
            self.assertEqual(result["family_p_value"], 1.0)
            self.assertEqual(result["holm_adjusted_p_value"], 1.0)
            self.assertFalse(result["holm_reject_at_0_05"])
            self.assertIn("NOT_AN_ENROLLED_PROSPECTIVE_COHORT", result["ineligibility_reasons"])
        self.assertEqual(report["status"], "NOT_ENROLLED")
        self.assertIsNone(report["preregistered_classification"])
        self.assertEqual(report["signal_authority"], "ZERO")
        self.assertFalse(report["adequacy_gates"]["complete_distinct_q1_q0_pairs"]["power_guarantee"])
        self.assertEqual([quarter["complete_pair_count"] for quarter in report["quarters"]], [52, 52, 48, 48])

    def test_secondary_pair_date_and_completeness_floors_cannot_be_traded_off(self):
        cases = ((199, 50, 199, "FEWER_THAN_200_COMPLETE_PAIRS"),
                 (200, 49, 200, "FEWER_THAN_50_ACTIVE_DATES"),
                 (211, 50, 200, "ENDPOINT_COMPLETENESS_BELOW_95_PERCENT"))
        for total, active, known_h10, reason in cases:
            pairs = tuple(replace(item, q1=replace(item.q1, h10_spy_excess_pp=None)) if i >= known_h10 else item
                          for i, item in enumerate(bulk_pairs(total, active)))
            result = evaluate_pb_d(pairs, context())["secondary"][SECONDARY_ENDPOINTS[1]]
            self.assertFalse(result["numerical_endpoint_gates_passed"])
            self.assertIn(reason, result["ineligibility_reasons"])
            self.assertEqual(result["family_p_value"], 1)
        # 200/210 is above 95%; the threshold does not round 200/211 upward.
        pairs = tuple(replace(item, q1=replace(item.q1, h10_spy_excess_pp=None)) if i >= 200 else item
                      for i, item in enumerate(bulk_pairs(210)))
        result = evaluate_pb_d(pairs, context())["secondary"][SECONDARY_ENDPOINTS[1]]
        self.assertTrue(result["numerical_endpoint_gates_passed"])

    def test_invalid_or_unknown_calendar_and_source_context_explicitly_block_tests(self):
        # Numeric breadth is deliberately sufficient, so these refusal reasons
        # cannot be explained by small n or unavailable endpoints. Dataset
        # status remains synthetic: these strings are not actual attestations.
        ready_metadata = dict(calendar_complete=True,
                              calendar_receipt_ref="SYNTHETIC-CALENDAR-NOT-A-REAL-RECEIPT",
                              integrity_audit_passed=True,
                              integrity_audit_receipt_ref="SYNTHETIC-AUDIT-NOT-A-REAL-RECEIPT",
                              frozen_matching_receipt_ref="SYNTHETIC-MATCHING-NOT-A-REAL-RECEIPT")
        cases = (("calendar_complete", False, "calendar", "FAIL"),
                 ("calendar_complete", None, "calendar", "UNKNOWN"),
                 ("integrity_audit_passed", False, "source_integrity", "FAIL"),
                 ("integrity_audit_passed", None, "source_integrity", "UNKNOWN"),
                 ("frozen_matching_receipt_ref", None, "frozen_pre_outcome_matching", "UNKNOWN"))
        for field_name, value, gate, state in cases:
            metadata = {**ready_metadata, field_name: value}
            report = evaluate_pb_d(bulk_pairs(), context(**metadata))
            self.assertEqual(report["secondary_context_gates"][gate]["status"], state)
            for result in report["secondary"].values():
                self.assertTrue(result["numerical_endpoint_gates_passed"])
                self.assertFalse(result["test_eligible"])
                self.assertIn(f"{gate.upper()}_NOT_CONFIRMED_VALID", result["ineligibility_reasons"])
                self.assertEqual(result["family_p_value"], 1.0)
                self.assertFalse(result["holm_reject_at_0_05"])
            self.assertEqual(report["status"], "NOT_ENROLLED")
        # An adverse H5 result is not a source-integrity failure and does not
        # disable numerical eligibility of the prespecified H10 contrast.
        negative_primary = tuple(replace(item, q1=replace(item.q1, h5_spy_excess_pp=-2.0))
                                 for item in bulk_pairs())
        report = evaluate_pb_d(negative_primary, context(**ready_metadata))
        self.assertTrue(report["primary_interval_is_adverse"])
        self.assertTrue(all(gate["status"] == "PASS" for gate in report["secondary_context_gates"].values()))
        later = report["secondary"][SECONDARY_ENDPOINTS[1]]
        self.assertTrue(later["numerical_endpoint_gates_passed"])
        self.assertEqual(later["ineligibility_reasons"], ("NOT_AN_ENROLLED_PROSPECTIVE_COHORT",))

    def test_units_coverage_denominators_and_fixed_enrollment_quarters(self):
        pairs = bulk_pairs()
        report = evaluate_pb_d(pairs, context(first_t2_count=500, complete_primary_exposure_count=400,
                                              eligible_q1_count=285))
        self.assertEqual(report["adequacy_gates"]["primary_exposure_coverage"]["status"], "PASS")
        self.assertEqual(report["adequacy_gates"]["matched_support"]["status"], "PASS")
        self.assertEqual(report["robustness_gates"]["practical_point_increment_at_least_2_pp"]["status"], "PASS")
        unknown = evaluate_pb_d(pairs, context())
        self.assertEqual(unknown["adequacy_gates"]["primary_exposure_coverage"]["status"], "UNKNOWN")
        self.assertEqual(unknown["adequacy_gates"]["matched_support"]["status"], "UNKNOWN")
        self.assertEqual(unknown["adequacy_gates"]["timing_root_price_version_integrity"]["status"], "UNKNOWN")
        self.assertEqual(unknown["robustness_gates"]["no_single_issuer_omission_sign_reversal"]["status"], "UNKNOWN")
        tiny_units = evaluate_pb_d((pair(0, treated=0.03, control=0.0),), context())
        self.assertEqual(tiny_units["robustness_gates"]["practical_point_increment_at_least_2_pp"]["status"], "FAIL")

    def test_missingness_range_retains_known_legs_and_original_pairs(self):
        pairs = (pair(0, 0, 5, 0), pair(1, 1, None, 1), pair(2, 1, 2, None))
        ctx = context(observed_cohort_h5_range_pp=(-10, 20),
                      observed_cohort_h5_range_receipt_ref="SYNTHETIC-RANGE-NOT-A-REAL-RECEIPT")
        report = evaluate_pb_d(pairs, ctx)
        scenarios = report["missingness"]["scenarios"]
        self.assertEqual(report["primary"]["equal_date_mean_increment_pp"], 5.0)
        self.assertEqual(scenarios["adverse_q1"]["point_estimate_pp"], -4.75)
        self.assertEqual(scenarios["favorable_q1"]["point_estimate_pp"], 10.25)
        self.assertEqual(len(scenarios["adverse_q1"]["imputations"]), 2)
        self.assertFalse(report["missingness"]["scenarios_are_identification_bounds"])
        self.assertEqual(report["robustness_gates"]["not_dependent_on_missing_outcome_sensitivity"]["status"], "FAIL")
        self.assertIsNone(pairs[1].q1.h5_spy_excess_pp)
        self.assertIsNone(pairs[2].q0.h5_spy_excess_pp)
        without_range = evaluate_pb_d(pairs, context())
        self.assertEqual(without_range["missingness"]["scenario_status"], "UNKNOWN_FULL_COHORT_OBSERVED_RANGE")
        self.assertEqual(without_range["robustness_gates"]["not_dependent_on_missing_outcome_sensitivity"]["status"], "UNKNOWN")
        with self.assertRaises(ValueError):
            evaluate_pb_d(pairs, context(observed_cohort_h5_range_pp=(0, 1)))

    def test_omission_requires_full_pool_evidence_and_preserves_issuer_outcomes(self):
        a, b = pair(0, 0, 3, 1), pair(1, 0, 6, 5)
        extra = Outcome("SYNTHETIC-UNMATCHED", "SYNTHETIC-EXTRA", h5_spy_excess_pp=8, entry_status="FILLED")
        pool = tuple(leg.issuer_id for item in (a, b) for leg in (item.q1, item.q0)) + (extra.issuer_id,)
        ctx = context(eligible_issuer_ids=pool, intc_issuer_ids=(),
                      eligible_pool_receipt_ref="SYNTHETIC-FULL-POOL-NOT-A-REAL-RECEIPT")
        omitted = OmissionSensitivity("ISSUER", "remove-original-control", (replace(a, q0=extra), b),
                                      omitted_issuer_ids=(a.q0.issuer_id,), eligible_q1_count=2,
                                      full_pool_rematch_receipt_ref="SYNTHETIC-REMATCH-NOT-A-REAL-RECEIPT")
        report = evaluate_pb_d((a, b), ctx, omissions=(omitted,))
        self.assertEqual(report["omission_sensitivity"]["records"][0]["estimate_pp"], -2.0)
        self.assertEqual(report["robustness_gates"]["no_single_issuer_omission_sign_reversal"]["status"], "FAIL")
        self.assertEqual(report["robustness_gates"]["no_intc_omission_sign_reversal"]["status"], "PASS")
        without_receipt = evaluate_pb_d((a, b), ctx, omissions=(replace(omitted, full_pool_rematch_receipt_ref=None),))
        self.assertEqual(without_receipt["robustness_gates"]["no_single_issuer_omission_sign_reversal"]["status"], "UNKNOWN")
        changed_outcome = replace(a, q1=replace(a.q1, h5_spy_excess_pp=100), q0=extra)
        with self.assertRaises(ValueError):
            evaluate_pb_d((a, b), ctx, omissions=(replace(omitted, pairs=(changed_outcome, b)),))
        with self.assertRaises(ValueError):
            evaluate_pb_d((a, b), ctx, omissions=(replace(omitted, pairs=(replace(a, q0=extra, session_index=1), b)),))

    def test_immutable_inputs_duplicate_issuers_unfilled_and_nan_rejected(self):
        a = pair(0)
        with self.assertRaises(FrozenInstanceError):
            a.q1.h5_spy_excess_pp = 999
        with self.assertRaises(ValueError):
            evaluate_pb_d((a, replace(a, pair_id="another-pair")), context())
        with self.assertRaises(ValueError):
            Outcome("SYNTHETIC", "SYNTHETIC", h5_spy_excess_pp=math.nan)
        with self.assertRaises(ValueError):
            Outcome("SYNTHETIC", "SYNTHETIC", h5_spy_excess_pp=0, entry_status="UNFILLED")
        with self.assertRaises(ValueError):
            Outcome("SYNTHETIC", "SYNTHETIC", h5_spy_excess_pp=3, h5_missing_reason="PENDING")
        with self.assertRaises(ValueError):
            evaluate_pb_d((a,), context(eligible_q1_count=0))
        intc = replace(a, q1=replace(a.q1, ticker_at_cut="INTC"))
        with self.assertRaises(ValueError):
            evaluate_pb_d((intc,), context(intc_issuer_ids=()))
        roots = ["SYNTHETIC-ROOT"]
        immutable = Outcome("SYNTHETIC", "SYNTHETIC", root_ids=roots)
        roots.append("LATER-MUTATION")
        self.assertEqual(immutable.root_ids, ("SYNTHETIC-ROOT",))


class TestFrozenDescriptiveOutcomes(unittest.TestCase):
    def test_fixed_cost_scenarios_use_basis_points_and_known_arm_denominators(self):
        pairs = (pair(0, 0, 1.0, 0.75), pair(1, 0, 0.25, 0.0),
                 pair(2, 1, 0.5, -0.25), pair(3, 2, 0.1, None))
        report = evaluate_pb_d(pairs, context())
        costs = report["fixed_round_trip_cost_scenarios"]
        scenarios = {item["round_trip_cost_bps"]: item for item in costs["scenarios"]}
        self.assertEqual(tuple(scenarios), (10, 25, 50))
        self.assertTrue(costs["gross_returns_remain_primary"])
        self.assertFalse(costs["measured_execution_costs"])
        self.assertEqual(report["primary"]["equal_date_mean_increment_pp"], 0.5)
        self.assertAlmostEqual(report["descriptive_horizons"]["h5"]["spy_excess_pp"]["q1"]["equal_issuer_mean_pp"], 0.4625)
        for bps, mean, positives in ((10, 0.3625, 3), (25, 0.2125, 2), (50, -0.0375, 1)):
            scenario = scenarios[bps]
            self.assertEqual(scenario["deduction_pp"], bps / 100)
            measure = scenario["horizons"]["h5"]["spy_excess_pp"]
            self.assertEqual(measure["q1"]["valid_mature_count"], 4)
            self.assertEqual(measure["q0"]["valid_mature_count"], 3)
            self.assertEqual(measure["q0"]["unknown_or_pending_count"], 1)
            self.assertEqual(measure["complete_pair_count"], 3)
            self.assertAlmostEqual(measure["q1"]["equal_issuer_mean_pp"], mean)
            # At each cost one treated return equals the deduction exactly;
            # net zero is not a positive outcome.
            self.assertEqual(measure["q1"]["strictly_positive_count"], positives)
            self.assertEqual(measure["q1"]["strictly_positive_rate"], positives / 4)
            self.assertEqual(measure["q0"]["strictly_positive_rate"], 1 / 3)
        q0_after_25 = scenarios[25]["horizons"]["h5"]["spy_excess_pp"]["q0"]
        self.assertAlmostEqual(q0_after_25["equal_issuer_mean_pp"], -1 / 12)
        h1 = scenarios[50]["horizons"]["h1"]["spy_excess_pp"]
        self.assertIsNone(h1["q1"]["equal_issuer_mean_pp"])
        self.assertIsNone(h1["q1"]["strictly_positive_rate"])
        self.assertEqual(report["status"], "NOT_ENROLLED")

    def test_identical_fixed_costs_cancel_in_paired_means_not_in_arm_hit_rates(self):
        pairs = []
        for original in (pair(0, 0, 1.0, 0.75), pair(1, 0, 0.25, 0), pair(2, 1, 0.5, -0.25)):
            legs = [replace(leg, h5_absolute_return_pp=leg.h5_spy_excess_pp + 1,
                            h5_sector_excess_pp=leg.h5_spy_excess_pp - 0.5)
                    for leg in (original.q1, original.q0)]
            pairs.append(replace(original, q1=legs[0], q0=legs[1]))
        report = evaluate_pb_d(tuple(pairs), context())
        for scenario in report["fixed_round_trip_cost_scenarios"]["scenarios"]:
            for measure in ("absolute_return_pp", "spy_excess_pp", "sector_excess_pp"):
                gross = report["descriptive_horizons"]["h5"][measure]
                net = scenario["horizons"]["h5"][measure]
                self.assertEqual(net["equal_date_mean_increment_pp"], 0.5)
                self.assertEqual(net["equal_pair_mean_increment_pp"], 1.25 / 3)
                self.assertEqual(net["equal_date_mean_increment_pp"], gross["equal_date_mean_increment_pp"])
                for arm in ("q1", "q0"):
                    self.assertAlmostEqual(net[arm]["equal_issuer_mean_pp"],
                                           gross[arm]["equal_issuer_mean_pp"] - scenario["deduction_pp"])
        self.assertEqual(len(report["secondary"]), 4)
        self.assertTrue(all(item["family_p_value"] == 1.0 for item in report["secondary"].values()))

    def test_h5_responder_persistence_uses_same_mature_issuers_and_zero_reversals(self):
        treated = ((4, 2, -1), (2, None, 0), (0, 10, 20), (None, 5, 10), (-3, 9, 10))
        controls = ((1, 0, 2), (-1, 5, 6), (2, -2, None), (None, 4, 5), (0, 3, 1))
        pairs = []
        for i, (q1, q0) in enumerate(zip(treated, controls)):
            original = pair(i, i)
            legs = [replace(leg, h5_spy_excess_pp=values[0], h10_spy_excess_pp=values[1],
                            h21_spy_excess_pp=values[2])
                    for leg, values in ((original.q1, q1), (original.q0, q0))]
            pairs.append(replace(original, q1=legs[0], q0=legs[1]))
        report = evaluate_pb_d(pairs, context())["h5_spy_responder_persistence"]
        self.assertTrue(report["descriptive_only"])
        q1 = report["arms"]["q1"]
        self.assertEqual(q1["h5_known_count"], 4)
        self.assertEqual(q1["h5_unknown_or_pending_count"], 1)
        self.assertEqual(q1["h5_responder_count"], 2)
        self.assertEqual(q1["h5_known_nonresponder_count"], 2)
        h10, h21 = q1["horizons"]["h10"], q1["horizons"]["h21"]
        self.assertEqual(h10["mature_known_denominator"], 1)
        self.assertEqual(h10["missing_or_pending_responder_count"], 1)
        self.assertEqual(h10["persistence_fraction"], 1)
        self.assertEqual(h10["reversal_fraction"], 0)
        self.assertEqual(h10["mean_later_cumulative_spy_excess_pp"], 2)
        self.assertEqual(h10["mean_h5_cumulative_spy_excess_pp_same_mature_responders"], 4)
        self.assertEqual(h10["mean_change_in_cumulative_spy_excess_pp"], -2)
        self.assertEqual(h21["mature_known_denominator"], 2)
        self.assertEqual(h21["persistence_fraction"], 0)
        self.assertEqual(h21["reversal_count"], 2)  # Later zero is a reversal.
        self.assertEqual(h21["reversal_fraction"], 1)
        self.assertEqual(h21["mean_later_cumulative_spy_excess_pp"], -0.5)
        self.assertEqual(h21["mean_change_in_cumulative_spy_excess_pp"], -3.5)
        q0 = report["arms"]["q0"]["horizons"]
        self.assertEqual(q0["h10"]["mature_known_denominator"], 2)
        self.assertEqual(q0["h10"]["reversal_count"], 2)
        self.assertEqual(q0["h10"]["mean_change_in_cumulative_spy_excess_pp"], -2.5)
        self.assertEqual(q0["h21"]["mature_known_denominator"], 1)
        self.assertEqual(q0["h21"]["persistence_fraction"], 1)
        self.assertEqual(q0["h21"]["mean_change_in_cumulative_spy_excess_pp"], 1)
        self.assertIsNone(h21["post_h5_drawdown_pp"])
        self.assertEqual(h21["post_h5_drawdown_status"], "UNKNOWN_POST_H5_PRICE_PATH_NOT_SUPPLIED")

    def test_no_responder_or_no_mature_later_outcome_never_becomes_zero_persistence(self):
        original = pair(0, treated=1, control=0)
        original = replace(original,
                           q1=replace(original.q1, h10_spy_excess_pp=None, h21_spy_excess_pp=None),
                           q0=replace(original.q0, h10_spy_excess_pp=None, h21_spy_excess_pp=None))
        persistence = evaluate_pb_d((original,), context())["h5_spy_responder_persistence"]
        for arm, responder_count in (("q1", 1), ("q0", 0)):
            self.assertEqual(persistence["arms"][arm]["h5_responder_count"], responder_count)
            for horizon in persistence["arms"][arm]["horizons"].values():
                self.assertEqual(horizon["mature_known_denominator"], 0)
                self.assertEqual(horizon["missing_or_pending_responder_count"], responder_count)
                self.assertIsNone(horizon["persistence_fraction"])
                self.assertIsNone(horizon["reversal_fraction"])
                self.assertIsNone(horizon["mean_later_cumulative_spy_excess_pp"])
                self.assertIsNone(horizon["mean_change_in_cumulative_spy_excess_pp"])


class TestOHLCPaths(unittest.TestCase):
    def setUp(self):
        start = datetime(2020, 1, 1, 20, tzinfo=timezone.utc)
        self.before = tuple(OHLCBar((start + timedelta(days=i)).isoformat(), 101, 99, 100) for i in range(21))
        self.entry_at = (start + timedelta(days=21)).isoformat()
        self.cut = (start + timedelta(days=21, hours=-5, minutes=-45)).isoformat()
        self.expected = tuple((start + timedelta(days=22 + i)).isoformat() for i in range(21))

    def calculate(self, bars, **changes):
        arguments = dict(entry_close=100, entry_close_at=self.entry_at, decision_cut=self.cut,
                         pre_cut_bars=self.before, post_entry_bars=bars,
                         expected_pre_cut_closes=tuple(bar.close_at for bar in self.before),
                         expected_post_entry_closes=self.expected,
                         calendar_receipt_ref="SYNTHETIC-CALENDAR-NOT-A-REAL-RECEIPT",
                         price_basis_receipt_ref="SYNTHETIC-PRICE-BASIS-NOT-A-REAL-RECEIPT")
        arguments.update(changes)
        return compute_ohlc_path(**arguments)

    def test_path_excursions_drawdown_and_unambiguous_upper_before_lower(self):
        values = ((101, 99, 100), (104, 99, 103), (106, 102, 105), (103, 97, 98), (103, 100, 102))
        bars = tuple(OHLCBar(timestamp, *value) for timestamp, value in zip(self.expected, values))
        report = self.calculate(bars)
        h5 = report["horizons"]["h5"]
        self.assertEqual(report["atr20_at_cut"], 2)
        self.assertEqual(report["b20_at_cut"], 101)
        self.assertAlmostEqual(h5["mfe_pp"], 6)
        self.assertAlmostEqual(h5["mae_pp"], -3)
        self.assertAlmostEqual(h5["close_mae_pp"], -2)
        self.assertAlmostEqual(h5["close_peak_to_trough_drawdown_pp"], 100 * (98 / 105 - 1))
        self.assertTrue(report["h5_clean_liftoff"]["label"])
        self.assertEqual(report["h5_clean_liftoff"]["first_upper_session"], 2)
        self.assertEqual(report["h5_clean_liftoff"]["first_lower_session"], 4)
        self.assertEqual(report["h5_failed_breakout"]["status"], "NOT_APPLICABLE")
        self.assertIsNone(report["horizons"]["h10"]["mfe_pp"])

    def test_same_bar_order_remains_unknown_even_if_h5_close_is_below_entry(self):
        bars = tuple(OHLCBar(time, 103, 97, 99) for time in self.expected[:5])
        clean = self.calculate(bars)["h5_clean_liftoff"]
        self.assertIsNone(clean["label"])
        self.assertEqual(clean["reason"], "UNKNOWN_SAME_BAR_FIRST_CROSSING_ORDER")

    def test_atr_arithmetic_true_range_and_strict_failed_breakout_subset(self):
        # First range sees the prior 100 close: TR=10. The other nineteen
        # have TR=2, so ATR20=(10+19*2)/20=2.4, rather than a Wilder update.
        before = (self.before[0],) + tuple(OHLCBar(bar.close_at, 110, 108, 109) for bar in self.before[1:])
        bars = tuple(OHLCBar(time, 112, 108, 108.8) for time in self.expected[:5])
        at_threshold = self.calculate(bars, pre_cut_bars=before, entry_close=111)
        self.assertEqual(at_threshold["atr20_at_cut"], 2.4)
        self.assertEqual(at_threshold["b20_at_cut"], 110)
        self.assertFalse(at_threshold["h5_failed_breakout"]["label"])
        failed_bars = (replace(bars[0], close=108.7),) + bars[1:]
        failed = self.calculate(failed_bars, pre_cut_bars=before, entry_close=111)
        self.assertTrue(failed["h5_failed_breakout"]["label"])
        equality = self.calculate(bars, pre_cut_bars=before, entry_close=110)
        self.assertEqual(equality["h5_failed_breakout"]["status"], "NOT_APPLICABLE")
        self.assertIsNone(equality["h5_failed_breakout"]["label"])

    def test_missing_calendar_bar_never_shifts_horizon_or_becomes_false(self):
        bars = tuple(OHLCBar(time, 103, 99, 102) for time in self.expected[:5])
        missing_second = self.calculate((bars[0],) + bars[2:])
        self.assertEqual(missing_second["horizons"]["h5"]["observed_close_count"], 4)
        self.assertIsNone(missing_second["horizons"]["h5"]["absolute_return_pp"])
        self.assertIsNone(missing_second["h5_clean_liftoff"]["label"])
        missing_prior_close = self.calculate(bars, pre_cut_bars=self.before[1:])
        self.assertIsNone(missing_prior_close["atr20_at_cut"])
        self.assertEqual(missing_prior_close["b20_at_cut"], 101)
        no_basis = self.calculate(bars, price_basis_receipt_ref=None)
        self.assertIsNone(no_basis["horizons"]["h5"]["mfe_pp"])
        self.assertIsNone(no_basis["h5_clean_liftoff"]["label"])

    def test_pre_cut_missing_session_cannot_be_bridged_by_21_observed_bars(self):
        older_time = (datetime.fromisoformat(self.before[0].close_at) - timedelta(days=1)).isoformat()
        older = OHLCBar(older_time, 101, 99, 100)
        expected = (older_time,) + tuple(bar.close_at for bar in self.before)
        missing_inside_last_twenty = (older,) + self.before[:10] + self.before[11:]
        self.assertEqual(len(missing_inside_last_twenty), 21)
        report = self.calculate((), pre_cut_bars=missing_inside_last_twenty,
                                expected_pre_cut_closes=expected)
        self.assertEqual(report["expected_pre_cut_bar_count"], 22)
        self.assertEqual(report["missing_expected_pre_cut_bar_count"], 1)
        self.assertIsNone(report["atr20_at_cut"])
        self.assertIsNone(report["b20_at_cut"])
        # If the only missing slot is the prior close BEFORE the last twenty,
        # their highs still establish B20, but ATR20 remains unknown.
        no_prior = self.calculate((), pre_cut_bars=self.before[1:])
        self.assertIsNone(no_prior["atr20_at_cut"])
        self.assertEqual(no_prior["b20_at_cut"], 101)

    def test_pre_cut_scale_requires_explicit_calendar_and_receipt(self):
        for changes in ({"expected_pre_cut_closes": None}, {"calendar_receipt_ref": None}):
            report = self.calculate((), **changes)
            self.assertEqual(report["pre_cut_session_contiguity"], "UNKNOWN_EXPECTED_CALENDAR_OR_RECEIPT")
            self.assertIsNone(report["atr20_at_cut"])
            self.assertIsNone(report["b20_at_cut"])
        with self.assertRaises(ValueError):
            self.calculate((), expected_pre_cut_closes=tuple(bar.close_at for bar in self.before[1:]))
        with self.assertRaises(ValueError):
            self.calculate((), expected_pre_cut_closes=tuple(bar.close_at for bar in self.before) + (self.entry_at,))

    def test_pre_fill_future_and_naive_clocks_are_rejected(self):
        with self.assertRaises(ValueError):
            OHLCBar("2020-01-01", 101, 99, 100)
        with self.assertRaises(ValueError):
            self.calculate((OHLCBar(self.entry_at, 999, 1, 100),))
        with self.assertRaises(ValueError):
            self.calculate((), pre_cut_bars=self.before + (OHLCBar(self.entry_at, 101, 99, 100),))
        with self.assertRaises(ValueError):
            OHLCBar(self.entry_at, 100, 101, 100)


if __name__ == "__main__":
    unittest.main()
