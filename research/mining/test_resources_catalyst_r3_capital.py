"""Executable research counterexamples; not a production capital or forecast API."""
import unittest
from decimal import Decimal as D
from resources_catalyst_r3_capital import visible_events, reconcile_capital, settle_warrants, first_transition_cif


def event(key='CI', kind='common_issue', count=5286417, effective='2022-04-25', known='2022-07-25', recorded='2026-09-27', basis='GMIN_2022_common'):
    return dict(id=key,kind=kind,count=count,effective_on=effective,known_on=known,recorded_on=recorded,basis=basis)


class CapitalTests(unittest.TestCase):
    def test_delayed_disclosure_not_visible_at_transaction_date(self):
        self.assertEqual(visible_events([event()], '2022-07-22'), [])
    def test_disclosure_visible_in_date_precision_view(self):
        self.assertEqual(visible_events([event()], '2022-07-25'), [event()])
    def test_current_capture_does_not_prove_historical_possession(self):
        self.assertEqual(visible_events([event()], '2022-07-25','system_replay'), [])
    def test_replay_when_recorded_is_actually_available(self):
        e=event(recorded='2022-07-25')
        self.assertEqual(visible_events([e], '2022-07-25','system_replay'), [e])
    def test_known_future_commitment_remains_visible_not_issued(self):
        e=event(kind='proposed_issue',effective='2022-09-07',known='2022-07-22')
        self.assertEqual(visible_events([e],'2022-07-22'),[e])
    def test_bad_mode(self):
        with self.assertRaises(ValueError): visible_events([event()],'2022-07-25','invented')
    def test_noncanonical_date(self):
        with self.assertRaises(ValueError): visible_events([event(known='20220725')],'2022-07-25')
    def test_duplicate_native_event_requires_owner_resolution(self):
        with self.assertRaises(ValueError): visible_events([event(),event()],'2022-07-25')
    def test_missing_known_clock(self):
        e=event();e['known_on']=None
        with self.assertRaises(ValueError):visible_events([e],'2022-07-25')
    def test_real_sparse_common_bridge_preserves_gap(self):
        ev=[event(),event('T1',count=160062500,effective='2022-07-22',known='2022-07-22'),event('T2',count=29004265,effective='2022-09-07',known='2022-09-07')]
        r=reconcile_capital(241895914,ev,'2022-03-28','2023-04-28','GMIN_2022_common',447517060,False)
        self.assertIsInstance(r,dict)
        self.assertEqual(r['covered_total'],436249096)
        self.assertEqual(r['unexplained_net_movement'],11267964)
        self.assertIsNone(r['exact_total'])
        self.assertEqual(r['state'],'INCOMPLETE_CENSUS')
    def test_secondary_sale_does_not_reduce_common(self):
        r=reconcile_capital(100,[event(kind='secondary_trade',count=70)],'2022-03-28','2022-07-25','GMIN_2022_common',None,True)
        self.assertIsInstance(r,dict);self.assertEqual(r['exact_total'],100)
    def test_cumulative_report_not_second_issuance(self):
        ev=[event('T1',count=160062500),event('T2',count=29004265),event('ALL',kind='reported_total',count=189066765)]
        r=reconcile_capital(100,ev,'2022-03-28','2022-09-07','GMIN_2022_common',None,True)
        self.assertIsInstance(r,dict);self.assertEqual(r['exact_total'],189066865)
    def test_proposal_not_issuance_even_after_expected_date(self):
        r=reconcile_capital(100,[event(kind='proposed_issue',count=30)],'2022-03-28','2023-01-01','GMIN_2022_common',None,True)
        self.assertIsInstance(r,dict);self.assertEqual(r['exact_total'],100)
    def test_warrant_issue_not_common_shares(self):
        r=reconcile_capital(100,[event(kind='warrant_issue',count=30)],'2022-03-28','2023-01-01','GMIN_2022_common',None,True)
        self.assertIsInstance(r,dict);self.assertEqual(r['exact_total'],100)
    def test_later_known_exercise_excluded_from_earlier_count(self):
        r=reconcile_capital(100,[event(count=30)],'2022-03-28','2022-07-22','GMIN_2022_common',None,False)
        self.assertIsInstance(r,dict);self.assertEqual(r['covered_total'],100);self.assertIsNone(r['exact_total'])
    def test_coverage_boolean_cannot_hide_reconciliation_conflict(self):
        r=reconcile_capital(100,[],'2022-03-28','2022-07-22','GMIN_2022_common',101,True)
        self.assertIsInstance(r,dict);self.assertEqual(r['state'],'CONFLICT');self.assertIsNone(r['exact_total'])
    def test_zero_gap_does_not_certify_missing_inventory(self):
        r=reconcile_capital(100,[],'2022-03-28','2022-07-22','GMIN_2022_common',100,False)
        self.assertIsInstance(r,dict);self.assertIsNone(r['exact_total'])
    def test_wrong_share_basis(self):
        with self.assertRaises(ValueError):reconcile_capital(100,[event(basis='GMIN_2024_common')],'2022-03-28','2023-01-01','GMIN_2022_common',None,False)
    def test_boolean_count(self):
        with self.assertRaises(ValueError):reconcile_capital(True,[],'2022-03-28','2023-01-01','GMIN_2022_common',None,False)
    def test_unknown_event_kind(self):
        with self.assertRaises(ValueError):reconcile_capital(100,[event(kind='vibes')],'2022-03-28','2023-01-01','GMIN_2022_common',None,False)
    def test_actual_retirement_has_signed_effect(self):
        r=reconcile_capital(100,[event(kind='common_retirement',count=30)],'2022-03-28','2023-01-01','GMIN_2022_common',None,True)
        self.assertIsInstance(r,dict);self.assertEqual(r['exact_total'],70)
    def test_retirement_cannot_create_negative_count(self):
        with self.assertRaises(ValueError):reconcile_capital(10,[event(kind='common_retirement',count=30)],'2022-03-28','2023-01-01','GMIN_2022_common',None,True)
    def test_anchor_future_to_cutoff_refused(self):
        with self.assertRaises(ValueError):reconcile_capital(100,[],'2022-03-28','2022-03-01','GMIN_2022_common',None,True)


class WarrantsTests(unittest.TestCase):
    def test_2022_cash_election_terms(self):
        r=settle_warrants(11500000,'1','1.90','cash',True)
        self.assertIsInstance(r,dict);self.assertEqual((r['new_shares'],r['conditional_issuer_cash']),(D('11500000'),D('21850000')))
    def test_2024_unit_change_preserves_proceeds(self):
        r=settle_warrants(11500000,'.25','1.90','cash',True)
        self.assertIsInstance(r,dict);self.assertEqual((r['new_shares'],r['price_per_whole_share'],r['conditional_issuer_cash']),(D('2875000'),D('7.60'),D('21850000')))
    def test_cashless_terms_missing_withholds_share_count(self):
        r=settle_warrants(11500000,'1','1.90','cashless',True)
        self.assertIsInstance(r,dict);self.assertIsNone(r['new_shares']);self.assertEqual(r['conditional_issuer_cash'],D(0));self.assertEqual(r['state'],'CASHLESS_RATIO_UNBOUND')
    def test_qualified_synthetic_cashless_ratio_has_no_cash(self):
        r=settle_warrants(100,'1','2','cashless',True,cashless_shares_per_right='.6')
        self.assertIsInstance(r,dict);self.assertEqual((r['new_shares'],r['conditional_issuer_cash']),(D(60),D(0)))
    def test_eligibility_unknown_is_not_a_cash_receipt(self):
        r=settle_warrants(100,'1','2','cash',None)
        self.assertIsInstance(r,dict);self.assertIsNone(r['conditional_issuer_cash']);self.assertEqual(r['state'],'ELIGIBILITY_UNBOUND')
    def test_ineligible_withholds(self):
        r=settle_warrants(100,'1','2','cash',False)
        self.assertIsInstance(r,dict);self.assertIsNone(r['new_shares']);self.assertEqual(r['state'],'INELIGIBLE')
    def test_cashless_ratio_cannot_exceed_deliverable(self):
        with self.assertRaises(ValueError):settle_warrants(100,'.25','1.90','cashless',True,cashless_shares_per_right='.5')
    def test_invalid_rights_count(self):
        with self.assertRaises(ValueError):settle_warrants(True,'1','2','cash',True)
    def test_nonfinite_terms(self):
        with self.assertRaises(ValueError):settle_warrants(100,'NaN','2','cash',True)
    def test_zero_deliverable(self):
        with self.assertRaises(ValueError):settle_warrants(100,'0','2','cash',True)
    def test_unknown_settlement(self):
        with self.assertRaises(ValueError):settle_warrants(100,'1','2','guess',True)


def toy():
    return [dict(id='A',time=1,cause='equity_extinguished'),dict(id='B',time=1,cause='equity_extinguished'),dict(id='C',time=2,cause='delivery'),dict(id='D',time=2,cause='delivery')]


class TransitionTests(unittest.TestCase):
    def test_competing_failures_not_deleted(self):
        r=first_transition_cif(toy(),2)
        self.assertIsInstance(r,dict);self.assertEqual(r['cif'],{'delivery':D('.5'),'equity_extinguished':D('.5')});self.assertEqual(r['event_free'],D(0))
    def test_horizon_before_delivery(self):
        r=first_transition_cif(toy(),1)
        self.assertIsInstance(r,dict);self.assertEqual(r['cif']['delivery'],D(0));self.assertEqual(r['event_free'],D('.5'))
    def test_event_and_censor_same_time_use_same_risk_set(self):
        r=first_transition_cif([dict(id='A',time=1,cause='delivery'),dict(id='B',time=1,cause='censored')],1)
        self.assertIsInstance(r,dict);self.assertEqual(r['cif']['delivery'],D('.5'));self.assertEqual(r['event_free'],D('.5'))
    def test_no_extrapolation_past_censored_tail(self):
        r=first_transition_cif([dict(id='A',time=1,cause='censored')],2)
        self.assertIsInstance(r,dict);self.assertEqual(r['state'],'FOLLOWUP_EXHAUSTED');self.assertIsNone(r['cif']);self.assertIsNone(r['event_free'])
    def test_absorbed_population_does_not_invent_tail(self):
        r=first_transition_cif(toy(),20)
        self.assertIsInstance(r,dict);self.assertEqual(r['cif']['delivery'],D('.5'))
    def test_empty_corpus_refused(self):
        with self.assertRaises(ValueError):first_transition_cif([],2)
    def test_duplicate_identity_refused(self):
        with self.assertRaises(ValueError):first_transition_cif([toy()[0],toy()[0]],2)
    def test_unknown_cause_not_censor(self):
        with self.assertRaises(ValueError):first_transition_cif([dict(id='A',time=1,cause='unknown')],2)
    def test_interval_time_not_midpoint(self):
        with self.assertRaises(ValueError):first_transition_cif([dict(id='A',time=[1,3],cause='delivery')],2)
    def test_negative_time(self):
        with self.assertRaises(ValueError):first_transition_cif([dict(id='A',time=-1,cause='delivery')],2)
    def test_boolean_time(self):
        with self.assertRaises(ValueError):first_transition_cif([dict(id='A',time=True,cause='delivery')],2)
    def test_delayed_entry_not_implicitly_ignored(self):
        with self.assertRaises(ValueError):first_transition_cif([dict(id='A',time=2,cause='delivery',entry=1)],2)
    def test_multiple_absorbing_causes_not_one_success_bit(self):
        rows=[dict(id='A',time=1,cause='delivery'),dict(id='B',time=1,cause='equity_extinguished'),dict(id='C',time=1,cause='claim_settled')]
        r=first_transition_cif(rows,1,('delivery','equity_extinguished','claim_settled'))
        self.assertIsInstance(r,dict);self.assertAlmostEqual(sum(r['cif'].values()),D(1));self.assertEqual(r['cif']['delivery'],D(1)/3)
    def test_no_authority_from_toy_sample(self):
        r=first_transition_cif(toy(),2)
        self.assertIsInstance(r,dict);self.assertFalse(r['can_rank']);self.assertFalse(r['empirically_qualified'])

if __name__=='__main__':unittest.main(verbosity=2)
