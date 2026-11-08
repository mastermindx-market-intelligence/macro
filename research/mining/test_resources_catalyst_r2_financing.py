"""R2 research specimens; source arithmetic is not valuation/model qualification."""
import unittest
from decimal import Decimal as D
from resources_catalyst_r2_financing import (
    cost_bridge, draw_eligibility, loan_period, equal_principal_repayments,
    stream_life, acquisition_payment_paths, share_rollforward, research_eligibility,
)

class Costs(unittest.TestCase):
    def test_cash_and_economic_costs_remain_different(self):
        self.assertEqual(cost_bridge('427','49','18','21'),
            dict(cash_initial=D('476'), economic_initial=D('458'),
                 cash_remaining=D('455'), future_recoverable=D('18')))
    def test_tax_credit_is_not_current_cash(self):
        self.assertNotEqual(cost_bridge('427','49','18','21')['cash_remaining'],D('437'))
    def test_credit_above_tax_is_invalid(self):
        with self.assertRaises(ValueError): cost_bridge('427','49','50','21')
    def test_spent_above_cash_budget_is_flagged_not_negative_remaining(self):
        with self.assertRaises(ValueError): cost_bridge('427','49','18','500')
    def test_missing_costs_stay_unavailable(self):
        self.assertIsNone(cost_bridge('427',None,'18','21'))

class Draws(unittest.TestCase):
    def ready(self):
        return dict(cost_to_complete_funded=True, permits=True, security=True,
                    engineering_confirmation=True)
    def test_real_cash_threshold_not_met(self):
        r=draw_eligibility('stream','21','95','0','250',self.ready())
        self.assertEqual(r['state'],'NOT_ELIGIBLE')
        self.assertEqual(r['failed'],('minimum_project_spend',))
    def test_all_verified_conditions_are_eligibility_not_disbursement(self):
        r=draw_eligibility('stream','95','95','0','250',self.ready())
        self.assertEqual(r,dict(state='ELIGIBLE_NOT_DRAWN',failed=(),unknown=(),cash_received=None))
    def test_unknown_security_not_false_positive(self):
        c=self.ready();c['security']=None
        r=draw_eligibility('stream','95','95','0','250',c)
        self.assertEqual(r['state'],'UNVERIFIED')
        self.assertEqual(r['unknown'],('security',))
    def test_false_and_unknown_both_retained(self):
        c=self.ready();c['security']=None;c['permits']=False
        r=draw_eligibility('stream','95','95','0','250',c)
        self.assertEqual(r['state'],'NOT_ELIGIBLE')
        self.assertEqual(r['failed'],('permits',));self.assertEqual(r['unknown'],('security',))
    def test_loan_cannot_skip_stream_predecessor(self):
        self.assertEqual(draw_eligibility('loan','95','95','249','250',self.ready())['state'],'NOT_ELIGIBLE')
    def test_unknown_predecessor_remains_unknown(self):
        self.assertEqual(draw_eligibility('loan','95','95',None,'250',self.ready())['state'],'UNVERIFIED')
    def test_invalid_state_type_rejected(self):
        c=self.ready();c['permits']='true'
        with self.assertRaises(ValueError): draw_eligibility('stream','95','95','0','250',c)
    def test_missing_required_condition_rejected(self):
        c=self.ready();del c['security']
        with self.assertRaises(ValueError): draw_eligibility('stream','95','95','0','250',c)
    def test_unsupported_facility_rejected(self):
        with self.assertRaises(ValueError): draw_eligibility('equipment','95','95','0','250',self.ready())

class Loan(unittest.TestCase):
    def test_full_draw_has_legal_principal_and_less_cash(self):
        r=loan_period('75','0','75','0.05',False,'1',False)
        self.assertEqual(r['new_cash'],D('73.50'));self.assertEqual(r['closing_principal'],D('75'))
        self.assertEqual(r['cash_interest_and_fees'],D('8.0625'))
    def test_spread_is_added_to_sofr_not_the_whole_coupon(self):
        self.assertEqual(loan_period('75','42','0','0.05',False,'1',False)['coupon'],D('.1075'))
    def test_contract_completion_changes_margin(self):
        self.assertEqual(loan_period('75','42','0','0.05',True,'1',False)['coupon'],D('.0975'))
    def test_unknown_completion_withholds_step(self):
        self.assertIsNone(loan_period('75','42','0','0.05',None,'1',False))
    def test_missing_sofr_withholds(self):
        self.assertIsNone(loan_period('75','42','0',None,False,'1',False))
    def test_capitalization_is_debt_not_free_interest(self):
        r=loan_period('75','42','0','0.05',False,'1',True)
        self.assertEqual(r['interest'],D('4.515'))
        self.assertEqual(r['standby_fee'],D('.33'))
        self.assertEqual(r['cash_interest_and_fees'],D('0'))
        self.assertEqual(r['closing_principal'],D('46.845'))
    def test_coupon_completion_is_not_accepting_truthy_string(self):
        with self.assertRaises(ValueError): loan_period('75','42','0','0.05','commercial','1',False)
    def test_overdraw_rejected(self):
        with self.assertRaises(ValueError): loan_period('75','42','34','0.05',False,'1',False)
    def test_unrounded_cashflows_preserved(self):
        r=loan_period('75','0','42','0.05',False,'.25',True)
        self.assertEqual(r['new_cash'],D('41.16'))
        self.assertEqual(r['closing_principal'],D('43.21125'))
    def test_capitalized_fees_do_not_consume_undrawn_face_capacity(self):
        r=loan_period('75','42','33','0.05',False,'.25',True,capitalized_on_entry='4.845')
        self.assertEqual(r['undrawn_face'],D('0'))
        self.assertEqual(r['standby_fee'],D('0'))
        self.assertEqual(r['new_cash'],D('32.34'))
        self.assertEqual(r['closing_principal'],D('79.845')*(1+D('.1075')/4))
    def test_period_longer_than_year_requires_split(self):
        with self.assertRaises(ValueError): loan_period('75','42','0','0.05',False,'2',False)
    def test_repayment_fixed_base_not_declining_balance(self):
        r=equal_principal_repayments('75',10,'.075')
        self.assertEqual(r['installments'],tuple(D('5.625') for _ in range(10)))
        self.assertEqual(r['bullet'],D('18.75'))
        self.assertEqual(sum(r['installments'])+r['bullet'],D('75'))
    def test_repayment_includes_capitalized_base_when_supplied(self):
        r=equal_principal_repayments('46.845',10,'.075')
        self.assertEqual(r['bullet'],D('11.71125'))
    def test_invalid_amortization_mass(self):
        with self.assertRaises(ValueError): equal_principal_repayments('75',14,'.075')

class Stream(unittest.TestCase):
    def test_stated_life_output_does_not_reach_lower_rate(self):
        r=stream_life('1838000','300000','.125','.075','.20','1600')
        self.assertEqual(r['stream_oz'],D('229750'))
        self.assertEqual(r['net_revenue_transfer'],D('294080000'))
        self.assertEqual(r['remaining_threshold_oz'],D('70250'))
        self.assertEqual(r['output_needed_for_first_stepdown_oz'],D('2400000'))
        self.assertFalse(r['lower_tier_used'])
    def test_metal_revenue_conservation(self):
        r=stream_life('1838000','300000','.125','.075','.20','1600')
        self.assertEqual(r['operator_revenue']+r['net_revenue_transfer'],D('1838000')*1600)
    def test_stepdown_uses_delivered_balance_not_produced(self):
        r=stream_life('2500000','300000','.125','.075','.20','1600')
        self.assertEqual(r['stream_oz'],D('307500'));self.assertTrue(r['lower_tier_used'])
    def test_unknown_balance_withholds(self):
        self.assertIsNone(stream_life('1838000',None,'.125','.075','.20','1600'))
    def test_zero_output_not_missing(self):
        self.assertEqual(stream_life('0','300000','.125','.075','.20','1600')['stream_oz'],D('0'))

class Acquisition(unittest.TestCase):
    def test_normal_case_is_60_on_first_anniversary(self):
        r=acquisition_payment_paths('60','.5','5','.10')
        self.assertEqual(r['normal'],((1,D('60')),))
        self.assertEqual(r['defer'],((1,D('30')),(2,D('35'))))
    def test_deferral_cost_rate_is_on_30_not_60(self):
        self.assertEqual(acquisition_payment_paths('60','.5','5','.10')['one_year_extension_rate'],D(5)/30)
    def test_at_ten_percent_deferral_costs_more_pv(self):
        r=acquisition_payment_paths('60','.5','5','.10')
        self.assertGreater(r['pv_defer'],r['pv_normal'])
    def test_at_twenty_percent_pv_deferral_is_less(self):
        r=acquisition_payment_paths('60','.5','5','.20')
        self.assertLess(r['pv_defer'],r['pv_normal'])
    def test_no_claim_unless_commercial_date_resolved(self):
        r=acquisition_payment_paths('60','.5','5','.10')
        self.assertNotIn('calendar_due_date',r)
    def test_negative_premium_rejected(self):
        with self.assertRaises(ValueError): acquisition_payment_paths('60','.5','-5','.10')

class Shares(unittest.TestCase):
    # The numeric opening count below is an ASSUMED test fixture, not a qualified historical count.
    def changes(self):
        return [dict(date='2022-07-22',count=160062500,id='tranche1'),
                dict(date='2022-09-07',count=29004265,id='tranche2')]
    def test_future_issue_is_excluded(self):
        r=share_rollforward(258450295,'2022-07-17',self.changes(),'2022-07-22',True)
        self.assertEqual(r['shares'],418512795)
        self.assertEqual(r['included'],('tranche1',))
    def test_both_closed_issues_included(self):
        r=share_rollforward(258450295,'2022-07-17',self.changes(),'2022-09-07',True)
        self.assertEqual(r['shares'],447517060)
    def test_unknown_opening_not_backcast_from_year_end(self):
        r=share_rollforward(None,'2022-07-17',self.changes(),'2022-09-07',True)
        self.assertIsNone(r['shares']);self.assertEqual(r['known_issuance_delta'],189066765)
    def test_incomplete_census_withholds_exact_sharecount(self):
        self.assertIsNone(share_rollforward(258450295,'2022-07-17',self.changes(),'2022-09-07',False)['shares'])
    def test_duplicate_issue_identity_rejected(self):
        with self.assertRaises(ValueError):share_rollforward(1,'2022-07-17',self.changes()*2,'2022-09-07',True)
    def test_date_grammar_enforced(self):
        with self.assertRaises(ValueError):share_rollforward(1,'20220717',self.changes(),'2022-09-07',True)
    def test_before_baseline_rejected(self):
        with self.assertRaises(ValueError):share_rollforward(1,'2022-07-23',self.changes(),'2022-07-22',True)

class ResearchBoundary(unittest.TestCase):
    def case(self):
        return dict(native_security=True, dated_rights=True, technical_cashflows=True,
                    tax_timing=True, funding_conditions=True, diluted_capital=True,
                    common_valuation_date=True, market_reference=True, policy_permission=True)
    def test_unknown_dependency_never_becomes_zero_value(self):
        c=self.case();c['tax_timing']=None
        r=research_eligibility(c)
        self.assertEqual(r['state'],'WITHHELD');self.assertIsNone(r['equity_value'])
        self.assertEqual(r['unresolved'],('tax_timing',))
    def test_ready_inputs_never_manufacture_value_or_trade_authority(self):
        r=research_eligibility(self.case())
        self.assertEqual(r['state'],'INPUTS_COMPLETE_NOT_VALUED')
        self.assertIsNone(r['equity_value']);self.assertFalse(r['can_originate'])
    def test_truthy_string_not_qualification(self):
        c=self.case();c['dated_rights']='accepted'
        with self.assertRaises(ValueError):research_eligibility(c)

if __name__=='__main__':unittest.main(verbosity=2)
