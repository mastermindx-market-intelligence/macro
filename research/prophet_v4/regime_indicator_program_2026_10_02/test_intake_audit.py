import copy
import unittest
from intake_audit import (audit_comparison, audit_information_cut, digest,
                          summarize_effective_ledger)


def row(i, ret=2, outcome='T1_HIT', entry='2026-08-03'):
    return dict(id=i, stock_result_pct=ret, outcome=outcome, entry_date=entry)


def manifest():
    return dict(population_digest='population', decision_cut_digest='cuts',
                target_definition='next_open_to_close_stock_excess_v1', target_horizon=10,
                target_horizon_unit='exchange_sessions', cost_definition='cost_v1',
                evaluation_partition='untouched_test', information_vintage_policy='owner_v1',
                instrument_plane='XNYS_equity', feed='feed_v1', session='RTH',
                timezone='America/New_York', anchor='abs-session-2026-08-06',
                adjustment='split_v1', grain='1D', kernel_memory_law='fixed_decay_time_26sessions',
                species_id='existing_owner_species', completed_bars_only=True,
                warmup_qualified=True, selection_scope='frozen_family')


def evidence():
    return dict(id='obs', decision_at='2026-09-30T16:00:00-04:00',
                published_at='2026-09-30T19:00:00Z', captured_at='2026-09-30T19:05:00Z',
                vintage_qualification='owner_verified', lookback_qualification='owner_verified')


class LedgerTests(unittest.TestCase):
    def report(self, rows, q=(), r=()):
        return summarize_effective_ledger(rows, q, r, source_identity={'sha': 'frozen'})

    def test_quarantine_and_no_entry_never_enter_denominator(self):
        r=self.report([row('a', 10), row('q', 999), row('n', 999, 'NO_ENTRY')], ['q'])
        self.assertEqual(r['entered']['return_observed'],1)
        self.assertEqual(r['entered']['mean_stock_return_pct'],10)
        self.assertEqual(r['counts']['no_entry'],1)

    def test_reconstruction_not_pooled_into_unmarked(self):
        r=self.report([row('a',-2),row('r',100)],r=['r'])
        self.assertEqual(r['not_marked_reconstructed_entered']['mean_stock_return_pct'],-2)
        self.assertEqual(r['reconstructed_entered']['return_observed'],1)
        self.assertNotIn('live',r)

    def test_missing_return_not_zero(self):
        r=self.report([row('a',None),row('b',0),row('c',2)])['entered']
        self.assertEqual((r['return_missing'],r['return_observed'],r['flat']),(1,2,1))
        self.assertEqual(r['positive_fraction'],0.5)

    def test_duplicate_id_refused(self):
        with self.assertRaises(ValueError):self.report([row('a'),row('a')])

    def test_empty_id_refused(self):
        with self.assertRaises(ValueError):self.report([row('')])

    def test_absent_disposition_refused(self):
        for kw in ({'q':['missing']},{'r':['missing']}):
            with self.subTest(kw=kw), self.assertRaises(ValueError): self.report([row('a')],**kw)

    def test_unknown_outcome_refused(self):
        with self.assertRaises(ValueError):self.report([row('a',outcome='NEW_STATE')])

    def test_nonfinite_boolean_text_return_refused(self):
        for value in (float('nan'),float('inf'),True,'2'):
            with self.subTest(value=value),self.assertRaises(ValueError):self.report([row('a',value)])

    def test_missing_entry_not_formation_fallback(self):
        x=row('a',entry=None);x['formation_date']='2020-01-01'
        self.assertIn('unknown',self.report([x])['entry_month_closed_only'])

    def test_invalid_entry_refused(self):
        for value in ('2026-99-99','20260901',20260901):
            with self.subTest(value=value),self.assertRaises(ValueError):self.report([row('a',entry=value)])

    def test_zero_authority(self):
        self.assertFalse(any(self.report([row('a')])['authority'].values()))

    def test_empty_record_no_nan(self):
        r=self.report([]);self.assertIsNone(r['entered']['mean_stock_return_pct']);digest(r)

    def test_inputs_not_mutated(self):
        rows=[row('a')];before=copy.deepcopy(rows);self.report(rows);self.assertEqual(rows,before)


class TimingTests(unittest.TestCase):
    def test_aware_cross_timezone(self):
        self.assertTrue(audit_information_cut([evidence()])['consistent'])

    def test_late_capture_refused_even_early_publication(self):
        x=evidence();x['captured_at']='2026-09-30T21:00:00Z'
        self.assertIn('future_information',audit_information_cut([x])['checks'][0]['reasons'])

    def test_late_publication_refused_even_early_capture(self):
        x=evidence();x['published_at']='2026-10-01T00:00:00Z'
        self.assertFalse(audit_information_cut([x])['consistent'])

    def test_date_only_unknown_not_midnight(self):
        for field in ('published_at','captured_at','decision_at'):
            with self.subTest(field=field):
                x=evidence();x[field]='2026-09-30'
                self.assertFalse(audit_information_cut([x])['consistent'])

    def test_no_vintage_or_window_inference(self):
        for field in ('vintage_qualification','lookback_qualification'):
            with self.subTest(field=field):
                x=evidence();x.pop(field);self.assertFalse(audit_information_cut([x])['consistent'])

    def test_empty_not_pass(self):self.assertFalse(audit_information_cut([])['consistent'])

    def test_duplicate_evidence_refused(self):
        with self.assertRaises(ValueError):audit_information_cut([evidence(),evidence()])

    def test_exact_cut_allowed(self):
        x=evidence();x['captured_at']=x['decision_at'];self.assertTrue(audit_information_cut([x])['consistent'])


class ComparisonTests(unittest.TestCase):
    def pair(self):
        a=manifest();b=manifest();b['grain']='3D';return a,b

    def test_matched_memory_grain(self):
        a,b=self.pair();self.assertTrue(audit_comparison(a,b,contrast='grain_memory_matched')['consistent'])

    def test_same_nominal_period_not_same_decay_time(self):
        a,b=self.pair();b['kernel_memory_law']='26_three_session_bars'
        self.assertIn('confounded:kernel_memory_law',audit_comparison(a,b,contrast='grain_memory_matched')['reasons'])

    def test_unpaired_each_identity_field(self):
        from intake_audit import IDENTITY
        for key in IDENTITY:
            with self.subTest(key=key):
                a,b=self.pair();b[key]='changed'
                self.assertFalse(audit_comparison(a,b,contrast='policy_bundle')['consistent'])

    def test_clock_confound_each_field(self):
        from intake_audit import CLOCK
        for key in CLOCK:
            with self.subTest(key=key):
                a,b=self.pair();b[key]='changed'
                self.assertFalse(audit_comparison(a,b,contrast='grain_memory_matched')['consistent'])

    def test_missing_identity_not_equal_missing(self):
        a,b=self.pair();a.pop('target_definition');b.pop('target_definition')
        self.assertFalse(audit_comparison(a,b,contrast='grain_memory_matched')['consistent'])

    def test_partial_and_warmup_unknown_rejected(self):
        for field in ('completed_bars_only','warmup_qualified'):
            with self.subTest(field=field):
                a,b=self.pair();b[field]=False
                self.assertFalse(audit_comparison(a,b,contrast='grain_memory_matched')['consistent'])

    def test_per_security_winner_lookup_refused(self):
        a,b=self.pair();b['selection_scope']='per_security_outcome_argmax'
        self.assertFalse(audit_comparison(a,b,contrast='policy_bundle')['consistent'])

    def test_bundle_cannot_claim_pure_grain(self):
        a,b=self.pair();b['session']='24H';b['kernel_memory_law']='different'
        self.assertTrue(audit_comparison(a,b,contrast='policy_bundle')['consistent'])
        self.assertFalse(audit_comparison(a,b,contrast='grain_memory_matched')['consistent'])

    def test_self_comparison_rejected(self):
        a=manifest();self.assertFalse(audit_comparison(a,a,contrast='kernel')['consistent'])

    def test_digest_bound_to_content(self):
        a,b=self.pair();first=audit_comparison(a,b,contrast='policy_bundle')
        b['target_horizon']=20;second=audit_comparison(a,b,contrast='policy_bundle')
        self.assertNotEqual(first['right_digest'],second['right_digest'])

    def test_dictionary_order_invariant(self):
        a=manifest();self.assertEqual(digest(a),digest(dict(reversed(list(a.items())))))

    def test_unknown_contrast_refused(self):
        a,b=self.pair()
        with self.assertRaises(ValueError):audit_comparison(a,b,contrast='best_sharpe')

    def test_nonfinite_metadata_not_serialized(self):
        a,b=self.pair();b['target_horizon']=float('nan')
        with self.assertRaises(ValueError):audit_comparison(a,b,contrast='policy_bundle')

    def test_run_id_difference_not_a_treatment(self):
        a=manifest();b=manifest();b['run_id']='another run'
        self.assertIn('no_declared_treatment_difference',audit_comparison(a,b,contrast='kernel')['reasons'])

    def test_bad_horizon_even_when_equal(self):
        for value in (0,-1,True,'10'):
            with self.subTest(value=value):
                a,b=self.pair();a['target_horizon']=b['target_horizon']=value
                self.assertFalse(audit_comparison(a,b,contrast='policy_bundle')['consistent'])

    def test_native_bars_not_common_economic_horizon(self):
        a,b=self.pair();a['target_horizon_unit']=b['target_horizon_unit']='native_bars'
        self.assertFalse(audit_comparison(a,b,contrast='grain_memory_matched')['consistent'])

    def test_missing_selection_law_refused(self):
        a,b=self.pair();a.pop('selection_scope');b.pop('selection_scope')
        self.assertFalse(audit_comparison(a,b,contrast='policy_bundle')['consistent'])


if __name__=='__main__': unittest.main()
