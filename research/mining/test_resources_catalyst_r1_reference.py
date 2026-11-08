"""Research-only arithmetic/admission examples, not the production owner suite."""
import unittest
from decimal import Decimal as D
from resources_catalyst_r1_reference import (
    available_funding, stream_cashflow, equity_raise, equity_price, net_return,
    funding_path, probability_weighted_return, reconcile_total, evidence_admissible,
)

class ReferenceTests(unittest.TestCase):
    def test_conditional_commitment_not_spendable(self):
        items=[dict(id='cash',amount='38',currency='USD',availability='AVAILABLE'),
               dict(id='facility',amount='131',currency='USD',availability='CONDITIONAL')]
        self.assertEqual(available_funding(items,'USD'),
                         {'known_available':D('38'),'complete':True,'excluded':('facility',),'unknown':()})
    def test_reported_cash_without_use_rights_remains_unknown(self):
        items=[dict(id='cash',amount='38',currency='USD',availability='UNKNOWN')]
        self.assertEqual(available_funding(items,'USD'),
                         {'known_available':D('0'),'complete':False,'excluded':(),'unknown':('cash',)})
    def test_other_project_cash_not_fungible(self):
        items=[dict(id='A',amount='19',currency='USD',availability='AVAILABLE'),
               dict(id='V',amount='16',currency='USD',availability='RESTRICTED'),
               dict(id='group',amount='7',currency='USD',availability='UNKNOWN')]
        self.assertEqual(available_funding(items,'USD'),
                         {'known_available':D('19'),'complete':False,'excluded':('V',),'unknown':('group',)})
    def test_duplicate_facility_rejected(self):
        x=dict(id='A',amount='1',currency='USD',availability='AVAILABLE')
        with self.assertRaises(ValueError): available_funding([x,x],'USD')
    def test_fx_not_silently_combined(self):
        x=dict(id='A',amount='1',currency='CAD',availability='AVAILABLE')
        with self.assertRaises(ValueError): available_funding([x],'USD')
    def test_unknown_amount_not_zero(self):
        x=dict(id='A',amount=None,currency='USD',availability='AVAILABLE')
        self.assertEqual(available_funding([x],'USD'),
                         {'known_available':D('0'),'complete':False,'excluded':(),'unknown':('A',)})
    def test_nonfinite_funding_rejected(self):
        x=dict(id='A',amount='NaN',currency='USD',availability='AVAILABLE')
        with self.assertRaises(ValueError): available_funding([x],'USD')
    def test_stream_12_5_percent_with_20_percent_payment(self):
        self.assertEqual(stream_cashflow('100000','300000','.125','.075','.20','1600'),
            {'stream_ounces':D('12500'),'retained_revenue':D('144000000'),
             'threshold_remaining':D('287500'),'retained_spot_fraction':D('.90')})
    def test_stream_threshold_is_delivered_not_produced_ounces(self):
        # Production of 300,000 oz has delivered only 37,500 oz into the threshold.
        x=stream_cashflow('300000','300000','.125','.075','.20','1600')
        self.assertIsNotNone(x)
        if x is not None: self.assertEqual(x['threshold_remaining'],D('262500'))
    def test_stream_crossing_splits_period(self):
        # 80,000 produced at 12.5% -> last 10,000 threshold ounces; rest at 7.5%.
        self.assertEqual(stream_cashflow('100000','10000','.125','.075','.20','1600'),
            {'stream_ounces':D('11500'),'retained_revenue':D('145280000'),
             'threshold_remaining':D('0'),'retained_spot_fraction':D('.908')})
    def test_unknown_stream_balance_withholds(self):
        self.assertIsNone(stream_cashflow('100000',None,'.125','.075','.20','1600'))
    def test_bad_stream_fraction_rejected(self):
        with self.assertRaises(ValueError): stream_cashflow('1','1','1.2','.075','.20','1600')
    def test_equity_fee_grossup(self):
        self.assertEqual(equity_raise('160','.05','2'),
                         {'gross':D('160')/D('.95'),'fees':D('160')/D('.95')*D('.05'),
                          'new_shares':D('160')/D('.95')/D('2')})
    def test_price_zero_cannot_finance(self):
        with self.assertRaises(ValueError): equity_raise('160','.05','0')
    def test_shareholder_bridge_after_funding(self):
        self.assertEqual(equity_price('600','30','20','100','100',D('160')/D('.95')/D('2')),
                         D('550')/(D('100')+D('160')/D('.95')/D('2')))
    def test_success_does_not_guarantee_positive_stock_return(self):
        p=equity_price('600','30','20','100','100',D('160')/D('.95')/D('2'))
        self.assertIsNotNone(p)
        if p is not None: self.assertLess(net_return(p,'3','.005','.005'),D('0'))
    def test_liquidation_cannot_have_negative_equity_price(self):
        self.assertEqual(equity_price('110','30','5','160','100','0'),D('0'))
    def test_liquidation_total_return_includes_purchase_cost_denominator(self):
        self.assertEqual(net_return('0','3','.005','.005'),D('-1'))
    def test_missing_equity_input_withholds(self):
        self.assertIsNone(equity_price(None,'30','20','100','100','0'))
    def test_negative_sharecount_rejected(self):
        with self.assertRaises(ValueError): equity_price('600','30','20','100','100','-2')
    def test_late_funding_does_not_erase_interim_cash_breach(self):
        self.assertEqual(funding_path('10',[('2024-01-01','-15'),('2024-02-01','20')]),
            {'closing_cash':D('15'),'minimum_cash':D('-5'),'first_breach':'2024-01-01'})
    def test_same_date_flows_net_as_period_without_intraday_claim(self):
        self.assertEqual(funding_path('10',[('2024-01-01','-15'),('2024-01-01','20')]),
            {'closing_cash':D('15'),'minimum_cash':D('10'),'first_breach':None})
    def test_funding_dates_require_canonical_calendar_dates(self):
        # A basic ISO spelling would otherwise sort after a later dashed date.
        with self.assertRaises(ValueError):
            funding_path('10', [('20240110','-15'), ('2024-02-01','20')])
    def test_unknown_probability_not_fabricated(self):
        self.assertIsNone(probability_weighted_return([None,'.5'],['.2','-.3']))
    def test_probability_mass_must_reconcile(self):
        with self.assertRaises(ValueError): probability_weighted_return(['.4','.4'],['.2','-.3'])
    def test_synthetic_weighted_return_arithmetic(self):
        self.assertEqual(probability_weighted_return(['.6','.4'],['.2','-.3']),D('0'))
    def test_reported_total_preserved_when_sum_disagrees(self):
        self.assertEqual(reconcile_total('567',['454','89','25']),
                         {'reported':D('567'),'calculated':D('568'),'residual':D('1'),'exact_match':False})
    def test_reported_liquidity_total_reconciles(self):
        self.assertEqual(reconcile_total('169',['131','38']),
                         {'reported':D('169'),'calculated':D('169'),'residual':D('0'),'exact_match':True})
    def test_public_reconstruction_not_system_replay(self):
        self.assertEqual(evidence_admissible('2023-11-14T23:59:59+00:00','2026-09-27T04:35:00+00:00',
                         '2023-11-15T00:00:00+00:00','public_reconstruction'),True)
        self.assertEqual(evidence_admissible('2023-11-14T23:59:59+00:00','2026-09-27T04:35:00+00:00',
                         '2023-11-15T00:00:00+00:00','system_replay'),False)
    def test_later_administration_banner_rejected_at_old_cutoff(self):
        self.assertEqual(evidence_admissible('2024-05-16T23:59:59+00:00','2026-09-27T04:35:00+00:00',
                         '2023-11-15T00:00:00+00:00','public_reconstruction'),False)
    def test_date_only_publication_not_intraday_known(self):
        self.assertEqual(evidence_admissible('2023-11-14T23:59:59+00:00','2026-09-27T04:35:00+00:00',
                         '2023-11-14T12:00:00+00:00','public_reconstruction'),False)
    def test_naive_clock_rejected(self):
        with self.assertRaises(ValueError): evidence_admissible('2023-11-14','2026-09-27','2023-11-15','public_reconstruction')
    def test_bad_time_mode_rejected(self):
        with self.assertRaises(ValueError): evidence_admissible('2023-01-01T00:00:00Z','2023-01-01T00:00:00Z','2023-01-02T00:00:00Z','invented')

if __name__=='__main__': unittest.main(verbosity=2)
