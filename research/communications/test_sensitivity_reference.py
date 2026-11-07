"""Tests of fixed research experiments, not any Mastermind application."""
from fractions import Fraction as F
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).with_name('replay_communications_sensitivity_examples.py')
spec = importlib.util.spec_from_file_location('sensitivity_reference', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SensitivityReferenceTests(unittest.TestCase):
    def case(self, name):
        cases = module.build_examples()
        self.assertIn(name, cases)
        return cases[name]['values']

    def test_roster_and_research_boundary(self):
        cases = module.build_examples()
        self.assertEqual(set(cases), {f'SX{i:02d}' for i in range(1, 19)})
        self.assertTrue(all(c['kind'] == 'synthetic_reference_only' for c in cases.values()))

    def test_observed_slope_does_not_identify_marginal_profit(self):
        c = self.case('SX01')
        self.assertEqual(c['observed_a'], c['observed_b'])
        self.assertEqual(c['forecast_a'], 34)
        self.assertEqual(c['forecast_b'], 37)

    def test_volume_price_interaction_and_costs(self):
        c = self.case('SX02')
        self.assertEqual(c['revenue_before'], 100)
        self.assertEqual(c['revenue_after'], F('112.2'))
        self.assertEqual(c['profit_before'], 40)
        self.assertEqual(c['profit_after'], 39)

    def test_migration_is_not_all_incremental_demand(self):
        c = self.case('SX03')
        self.assertEqual(c['before_contribution'], 80)
        self.assertEqual(c['after_migration_only'], 74)
        self.assertEqual(c['incremental_units_needed'], 10)
        self.assertEqual(c['after_hurdle'], 80)

    def test_aggregate_cost_rate_can_change_without_contract_change(self):
        c = self.case('SX04')
        self.assertEqual(c['aggregate_rate_before'], F('.18'))
        self.assertEqual(c['aggregate_rate_after'], F('.14'))
        self.assertEqual(c['component_rate_changes'], [0, 0])

    def test_presentation_growth_is_not_additional_profit(self):
        c = self.case('SX05')
        self.assertEqual(c['revenue_delta'], 15)
        self.assertEqual(c['cost_delta'], 15)
        self.assertEqual(c['profit_delta'], 0)

    def test_platform_workload_can_outgrow_paid_activity(self):
        c = self.case('SX06')
        self.assertEqual(c['retained_fees_before'], 200)
        self.assertEqual(c['retained_fees_after'], 220)
        self.assertEqual(c['profit_before'], 50)
        self.assertEqual(c['profit_after'], 45)

    def test_channel_mix_requires_channel_contribution_economics(self):
        c = self.case('SX07')
        self.assertEqual(c['contribution_before'], 42)
        self.assertEqual(c['contribution_after'], 45)
        self.assertEqual(c['total_receipts_delta'], 0)

    def test_working_capital_uses_collection_base_not_net_fees(self):
        c = self.case('SX08')
        self.assertEqual(c['funding_requirement'], 100)
        self.assertEqual(c['wrong_net_fee_estimate'], 10)
        self.assertEqual(c['loss_as_fraction_of_fee'], F('.1'))

    def test_capacity_step_invalidates_linear_extrapolation(self):
        c = self.case('SX09')
        self.assertEqual(c['first_increment'], -3)
        self.assertEqual(c['next_increment'], 5)

    def test_book_depreciation_change_is_not_itself_cash_creation(self):
        c = self.case('SX10')
        self.assertEqual(c['ebit_before'], 100)
        self.assertEqual(c['ebit_after'], 125)
        self.assertEqual(c['cash_before'], c['cash_after'])
        self.assertEqual(c['cash_after'], 50)

    def test_income_and_shares_must_both_enter_eps(self):
        c = self.case('SX11')
        self.assertEqual(c['earnings_growth'], F('.08'))
        self.assertEqual(c['share_growth'], F('.10'))
        self.assertEqual(c['eps_growth'], -F(1, 55))

    def test_fair_value_buyback_can_raise_eps_without_value_per_share(self):
        c = self.case('SX12')
        self.assertEqual(c['fair_price_value'], 10)
        self.assertGreater(c['under_value_price'], 10)
        self.assertLess(c['over_value_price'], 10)
        self.assertEqual(c['mechanical_eps_after'], F(10, 9))

    def test_same_future_award_claim_is_not_charged_twice(self):
        c = self.case('SX13')
        self.assertEqual(c['cash_cost_representation'], 800)
        self.assertEqual(c['separate_claim_representation'], 800)
        self.assertEqual(c['double_charge_error'], 600)
        self.assertEqual(c['after_distinct_existing_claim'], 750)

    def test_growth_value_depends_on_incremental_return(self):
        c = self.case('SX14')
        self.assertGreater(c['high_return_g4'], c['high_return_g2'])
        self.assertEqual(c['equal_return_g4'], c['equal_return_g2'])
        self.assertLess(c['low_return_g4'], c['low_return_g2'])

    def test_one_multiple_does_not_reveal_one_market_belief(self):
        c = self.case('SX15')
        self.assertEqual(c['required_return_k10'], F('.1875'))
        self.assertEqual(c['required_return_k9'], F(3, 28))
        self.assertEqual(c['multiple_ceiling'], F(100, 7))
        self.assertIsNone(c['fifteen_times_solution'])

    def test_growth_and_multiple_changes_compound(self):
        c = self.case('SX16')
        self.assertEqual(c['price_return'], -F('.04'))
        self.assertNotEqual(c['price_return'], c['wrong_additive_return'])

    def test_joint_scenarios_preserve_dependence(self):
        c = self.case('SX17')
        self.assertEqual(c['mean_joint_revenue'], 96)
        self.assertEqual(c['product_of_means'], 100)

    def test_investment_hurdle_accounts_for_delay(self):
        c = self.case('SX18')
        self.assertAlmostEqual(float(c['annual_cash_hurdle']), 263.7974807947454, places=9)
        self.assertEqual(c['delayed_hurdle'], c['annual_cash_hurdle'] * F('1.1'))
        self.assertEqual(c['revenue_hurdle'], c['annual_cash_hurdle'] / F('.4'))
        self.assertEqual(c['npv_at_hurdle'], 0)

    def test_invalid_stable_growth_assumptions_refuse(self):
        fn = getattr(module, '_stable_value', None)
        self.assertTrue(callable(fn))
        for g, k, r in [('0.10','0.10','0.20'), ('0.11','0.10','0.20'),
                        ('0.03','0.10','0'), ('0.07','0.10','0.06')]:
            with self.subTest(g=g, k=k, r=r), self.assertRaises(ValueError):
                fn(F(100), F(g), F(k), F(r))

    def test_no_probability_or_live_issuer_target_is_created(self):
        cases = module.build_examples()
        self.assertEqual(len(cases), 18)
        for c in cases.values():
            self.assertNotIn('ticker', c)
            self.assertNotIn('target_price', c)
            self.assertNotIn('native_id', c)

if __name__ == '__main__':
    unittest.main()
