"""Original synthetic mathematics only. No native engine, owner store or market data."""
from copy import deepcopy
import math
import unittest
import oracle as o


class MathematicalConformance(unittest.TestCase):
    def close(self, actual, expected, places=12):
        self.assertIsInstance(actual, (float, int))
        self.assertNotIsInstance(actual, bool)
        self.assertTrue(math.isfinite(actual))
        self.assertAlmostEqual(actual, expected, places=places)

    def test_01_normalize_cap_and_float_values(self):
        self.assertEqual(o.normalize_positive([1, 3]), (0.25, 0.75))
        self.assertEqual(o.normalize_positive([100 * .5, 100 * 1.0]), (1/3, 2/3))

    def test_02_inverse_vol_target_is_not_low_vol_screen(self):
        self.assertEqual(o.normalize_positive([1/.1, 1/.2]), (2/3, 1/3))

    def test_03_capped_weights_feasible(self):
        result = o.capped_weights([90, 5, 5], .5)
        self.assertIsInstance(result, tuple)
        self.assertEqual(result, (.5, .25, .25))

    def test_04_infeasible_cap_refused(self):
        with self.assertRaisesRegex(ValueError, "INFEASIBLE"):
            o.capped_weights([900, 40, 30, 20, 10], .05)

    def test_05_exact_cap_boundary(self):
        self.assertEqual(o.capped_weights([3, 2, 1, 1], .25), (.25, .25, .25, .25))

    def test_06_invalid_scores_refused(self):
        for values in ([0, 0], [1, -1], [True, 1], [1, float('nan')]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                o.normalize_positive(values)

    def test_07_strict_portfolio_return(self):
        self.close(o.strict_return([.25, .75], [.1, -.1]), -.05)

    def test_08_unvalued_positive_holding_is_not_zero(self):
        self.assertIsNone(o.strict_return([.8, .2], [.1, None]))
        self.close(o.weight_coverage([.8, .2], [.1, None]), .8)

    def test_09_zero_position_missing_is_not_held_weight(self):
        self.close(o.strict_return([1.0, 0.0], [.1, None]), .1)

    def test_10_weights_are_not_silently_normalized(self):
        with self.assertRaises(ValueError):
            o.strict_return([.5, .4], [.1, .2])

    def test_11_negative_weight_is_not_long_only(self):
        with self.assertRaises(ValueError):
            o.strict_return([2, -1], [.1, .2])

    def test_12_nonfinite_return_refused(self):
        for v in [float('nan'), float('inf'), True]:
            with self.subTest(value=v), self.assertRaises(ValueError):
                o.strict_return([1], [v])

    def test_13_split_neutral_raw_claims(self):
        self.close(o.claims_return(100, [2 * 50]), 0)

    def test_14_cash_dividend_included_once(self):
        self.close(o.claims_return(100, [99], cash=2), .01)

    def test_15_spinoff_and_cash_merger_claims(self):
        self.close(o.claims_return(100, [80, .5 * 40]), 0)
        self.close(o.claims_return(100, [], cash=95), -.05)

    def test_16_known_zero_proceeds_are_minus_one(self):
        self.close(o.claims_return(100, [], cash=0), -1)

    def test_17_missing_action_value_is_not_zero(self):
        self.assertIsNone(o.claims_return(100, [80, None]))

    def test_18_monthly_drift_round_trip_zero(self):
        initial = [1/3] * 3
        first = [1.0, 0.0, 0.0]
        w1 = o.drift_weights(initial, first)
        self.assertIsInstance(w1, tuple)
        r1 = o.strict_return(initial, first)
        r2 = o.strict_return(w1, [-.5, 0, 0])
        self.close((1+r1)*(1+r2)-1, 0)
        self.assertEqual(w1, (.5, .25, .25))

    def test_19_daily_reset_round_trip_one_ninth(self):
        r1 = o.strict_return([1/3]*3, [1, 0, 0])
        r2 = o.strict_return([1/3]*3, [-.5, 0, 0])
        self.close(o.horizon_return([r1, r2], 2), 1/9)

    def test_20_missing_drift_cannot_reconstruct_weights(self):
        self.assertIsNone(o.drift_weights([.5, .5], [None, .1]))

    def test_21_insolvency_cannot_have_normalized_weights(self):
        with self.assertRaisesRegex(ValueError, "INSOLVENT"):
            o.drift_weights([1], [-1])

    def test_22_chain_keeps_null_gap(self):
        self.assertEqual(o.link_returns([.1, None, .2]), [100.0, 110.00000000000001, None, None])

    def test_23_known_bankruptcy_stops_following_chain(self):
        self.assertEqual(o.link_returns([-1, .2]), [100.0, 0.0, None])

    def test_24_five_returns_are_sufficient(self):
        self.close(o.horizon_return([.01]*5, 5), 1.01**5-1)

    def test_25_horizon_missing_is_not_compressed(self):
        self.assertIsNone(o.horizon_return([.01, None, .01, .01, .01], 5))
        self.assertIsNone(o.horizon_return([.01]*4, 5))

    def test_26_horizon_does_not_silently_use_extra_start(self):
        self.close(o.horizon_return([.90, .01, .01], 2), 1.01**2-1)

    def test_27_relative_is_not_percentage_point_difference(self):
        self.close(o.relative_return(.2, .1), 1.2/1.1-1)
        self.assertNotAlmostEqual(o.relative_return(.2, .1), .2-.1)

    def test_28_relative_zero_denominator_refused(self):
        with self.assertRaises(ValueError):
            o.relative_return(.1, -1)

    def test_29_equal_weight_concentration(self):
        result = o.concentration([.25]*4)
        self.assertIsInstance(result, dict)
        self.close(result['hhi'], .25)
        self.close(result['effective_n'], 4)
        self.close(result['top1'], .25)
        self.close(result['top5'], 1)

    def test_30_drift_changes_concentration(self):
        result = o.concentration([.5, .25, .25])
        self.assertIsInstance(result, dict)
        self.close(result['hhi'], .375)

    def test_31_partial_breadth_keeps_missing_denominator(self):
        result = o.advance_breadth([.1, 0, -.1, .2, None], [.2]*5)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['status'], 'PARTIAL')
        self.close(result['value'], .5)
        self.assertEqual((result['advancing'], result['unchanged'], result['declining'], result['missing']), (2,1,1,1))
        self.close(result['count_coverage'], .8)
        self.close(result['weight_coverage'], .8)

    def test_32_breadth_insufficient_is_null(self):
        result = o.advance_breadth([.1, None, None], [1/3]*3)
        self.assertIsInstance(result, dict)
        self.assertIsNone(result['value'])
        self.assertEqual(result['status'], 'UNAVAILABLE')

    def test_33_single_etf_does_not_manufacture_breadth(self):
        result = o.advance_breadth([.1], [1])
        self.assertIsInstance(result, dict)
        self.assertEqual(result['status'], 'UNAVAILABLE')

    def test_34_count_coverage_does_not_replace_weight_coverage(self):
        result = o.advance_breadth([None, .1, .2, .3, .4], [.8,.05,.05,.05,.05])
        self.assertIsInstance(result, dict)
        self.assertEqual(result['status'], 'UNAVAILABLE')

    def test_35_linked_attribution_reconciles(self):
        result = o.linked_contributions([{'A': .1, 'B': -.02}, {'A': -.05, 'B': .01}])
        self.assertIsInstance(result, dict)
        self.close(sum(result.values()), 1.08*.96-1)
        self.close(result['A'], .1*.96-.05)

    def test_36_downside_denominator_all_days(self):
        self.close(o.downside_deviation([-.1, .1], annualization=1), math.sqrt(.01/2))

    def test_37_zero_downside_is_sample_value(self):
        self.close(o.downside_deviation([0, .1], annualization=1), 0)

    def test_38_sample_volatility_ddof_one(self):
        self.close(o.sample_volatility([-.1, .1], annualization=1), math.sqrt(.02))

    def test_39_abnormality_uses_prior_only(self):
        self.close(o.prior_z(3, [0, 1, 2]), 2)

    def test_40_constant_baseline_is_unavailable(self):
        self.assertIsNone(o.prior_z(1, [0]*60))

    def test_41_tail_fractional_boundary_and_type7_quantile(self):
        result = o.tail_loss([i/100 for i in range(-20, 0)], .125)
        self.assertIsInstance(result, dict)
        self.close(result['var'], .17625)
        self.close(result['es'], .192)
        self.close(result['tail_mass'], 2.5)

    def test_42_signed_var_is_not_clipped(self):
        result = o.tail_loss([.1, .2, .3, .4], .25)
        self.assertIsInstance(result, dict)
        self.close(result['var'], -.175)

    def test_43_digest_order_independent(self):
        self.assertEqual(o.canonical_digest({'B': 2, 'A': 1}), o.canonical_digest({'A': 1, 'B': 2}))
        self.assertIsInstance(o.canonical_digest({'A': 1}), str)
        self.assertEqual(len(o.canonical_digest({'A': 1})), 64)

    def test_44_correction_changes_manifest_identity(self):
        self.assertNotEqual(o.canonical_digest({'source_revision': 'old', 'return': 0}), o.canonical_digest({'source_revision': 'corrected', 'return': 0}))

    def test_45_nan_json_refused(self):
        with self.assertRaises(ValueError):
            o.canonical_digest({'value': float('nan')})

    def test_46_materialization_time_is_outside_result_core(self):
        first = {'core': {'return': .05}, 'materialized_at': '2026-10-01T00:00:00Z'}
        second = deepcopy(first); second['materialized_at'] = '2026-10-02T00:00:00Z'
        self.assertEqual(o.canonical_digest(first['core']), o.canonical_digest(second['core']))
        self.assertNotEqual(o.canonical_digest(first), o.canonical_digest(second))


class PITPredicateConformance(unittest.TestCase):
    """Synthetic necessary-condition predicate; cannot authenticate owner receipts."""
    def setUp(self):
        self.receipt = {'pit': True, 'basket_id': 'fixture:basket:A', 'collection_state': 'COMPLETE',
                        'effective_from': '2026-09-01T00:00:00Z', 'effective_to': None,
                        'observed_at': '2026-09-01T00:01:00Z', 'known_at': '2026-09-01T00:02:00Z',
                        'source_published_at': '2026-09-01T00:00:00Z', 'public_availability_required': True}
        self.kw = {'basket_id': 'fixture:basket:A', 'selection_cutoff': '2026-09-02T00:00:00Z',
                   'holding_at': '2026-09-02T13:30:00Z'}

    def test_47_known_complete_observation_is_eligible(self):
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), True)

    def test_48_current_fallback_refused(self):
        self.receipt['pit'] = False
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), False)

    def test_49_future_known_at_refused(self):
        self.receipt['known_at'] = '2026-09-02T00:00:01Z'
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), False)

    def test_50_future_publication_refused(self):
        self.receipt['source_published_at'] = '2026-09-02T00:00:01Z'
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), False)

    def test_51_partial_collection_does_not_qualify(self):
        self.receipt['collection_state'] = 'PARTIAL'
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), False)

    def test_52_other_basket_observation_does_not_qualify(self):
        self.receipt['basket_id'] = 'fixture:basket:B'
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), False)

    def test_53_effective_to_is_exclusive(self):
        self.receipt['effective_to'] = self.kw['holding_at']
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), False)

    def test_54_naive_clock_refused(self):
        self.receipt['known_at'] = '2026-09-01T00:02:00'
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), False)

    def test_55_observation_after_knowledge_refused(self):
        self.receipt['observed_at'] = '2026-09-01T00:03:00Z'
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), False)

    def test_56_same_instant_selection_and_execution_not_assumed(self):
        self.kw['holding_at'] = self.kw['selection_cutoff']
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), False)

    def test_57_missing_public_clock_refused_when_required(self):
        self.receipt['source_published_at'] = None
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), False)

    def test_58_house_fact_does_not_invent_public_clock(self):
        self.receipt['public_availability_required'] = False
        self.receipt['source_published_at'] = None
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), True)

    def test_59_current_and_pit_synthetic_cohorts_differ(self):
        current = o.strict_return([.5,.5], [.1,0])
        pit = o.strict_return([.5,.5], [.1,-.1])
        self.assertIsInstance(current, float)
        self.assertIsInstance(pit, float)
        self.assertNotEqual(current, pit)
        self.assertAlmostEqual(current, .05)
        self.assertAlmostEqual(pit, 0)

    def test_60_complete_empty_is_not_qualified_population_measurement(self):
        # Eligibility of a collection is not proof that it contains usable members.
        self.assertIs(o.pit_eligible(self.receipt, **self.kw), True)
        with self.assertRaises(ValueError):
            o.strict_return([], [])


if __name__ == '__main__':
    unittest.main()
