"""Manual-source contract challenges. These are not PDF/model/product tests."""
import copy
import inspect
import json
from pathlib import Path
import unittest
import revision_oracle as oracle

ROOT=Path(__file__).resolve().parent
REAL={c['id']:c for c in json.loads((ROOT/'analyst_control_case.json').read_text())['claims']}
OLD=json.loads((ROOT/'public_control_case.json').read_text())['claims']

def pair(a='june_fixed',b='sept3_fixed'):
    return copy.deepcopy(REAL[a]),copy.deepcopy(REAL[b])

def is_(test, result, **expected):
    for key,value in expected.items():
        test.assertEqual(result.get(key),value,(key,result))

def profile(test,a,b):
    test.assertIn('comparison_mode',inspect.signature(oracle.compare).parameters,'explicit profile comparison missing')
    return oracle.compare(a,b,comparison_mode='constant_horizon_profile')

def reported(test,c):
    test.assertTrue(callable(getattr(oracle,'reported_change',None)),'source-reported change projection missing')
    return oracle.reported_change(c)

class AnalystContract(unittest.TestCase):
    def test_01_real_fixed_year_comparison(self):
        is_(self,oracle.compare(*pair()),status='revision',delta_low='-0.02',percent_low='-1.694915',comparison_scope='publisher_named_fixed_target',numeric_change_between_inputs=True)
    def test_02_repeat_is_not_another_cut(self):
        is_(self,oracle.compare(*pair('sept3_fixed','sept7_fixed')),status='repeated_reported_revision',delta_low='0',numeric_change_between_inputs=False)
    def test_03_same_value_without_explicit_change_is_unchanged(self):
        a,b=pair('sept3_fixed','sept7_fixed');b.pop('reported_prior');b.pop('explicit_revision')
        is_(self,oracle.compare(a,b),status='unchanged_value')
    def test_04_old_record_not_immediate_predecessor(self):
        r=oracle.compare(*pair())
        is_(self,r,quoted_prior_relation='matches_captured_earlier_value',immediate_predecessor_verified=False,first_ever_revision_date_known=False)
    def test_05_quoted_prior_not_matching_earlier_does_not_fake_chain(self):
        a,b=pair();b['reported_prior']['point']='1.17'
        is_(self,oracle.compare(a,b),status='revision',quoted_prior_relation='differs_from_captured_earlier_value',immediate_predecessor_verified=False)
    def test_06_rolling_horizon_is_not_fixed_target(self):
        is_(self,oracle.compare(*pair('aug_relative','sept_relative')),status='not_comparable',reason='unresolved_relative_target')
    def test_07_profile_requires_explicit_mode(self):
        r=profile(self,*pair('aug_relative','sept_relative'))
        is_(self,r,status='constant_horizon_profile_change',delta_low='-0.01',fixed_target_revision=False)
    def test_08_different_relative_labels_refused(self):
        a,b=pair('aug_relative','sept_relative');b['target']['label']='6M'
        is_(self,profile(self,a,b),status='not_comparable',reason='different_horizon')
    def test_09_different_year_refused(self):
        a,b=pair();b['target']['year']=2027
        is_(self,oracle.compare(a,b),status='not_comparable',reason='different_target')
    def test_10_unknown_fixing_disclosed(self):
        is_(self,oracle.compare(*pair()),fixing_convention_verified=False)
    def test_11_different_fixing_refused(self):
        a,b=pair();a['target']['fixing']='London_close';b['target']['fixing']='NY_close'
        is_(self,oracle.compare(a,b),status='not_comparable',reason='different_fixing_convention')
    def test_12_one_unknown_fixing_is_not_equivalence(self):
        a,b=pair();b['target']['fixing']='London_close'
        is_(self,oracle.compare(a,b),status='not_comparable',reason='different_fixing_convention')
    def test_13_market_forward_is_not_publisher_forecast(self):
        a,b=pair();b['source_role']='market_forward'
        is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_14_missing_target_refused(self):
        a,b=pair();del b['target'];is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_15_boolean_year_refused(self):
        a,b=pair();b['target']['year']=True;is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_16_average_and_endpoint_not_comparable(self):
        a,b=pair();b['target']['measure']='period_average'
        is_(self,oracle.compare(a,b),status='not_comparable',reason='different_target_measure')
    def test_17_unrecognized_target_fields_refused(self):
        a,b=pair();b['target']['invented_clock']='safe';is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_18_permission_precedes_content(self):
        a,b=pair();b['allowed_for_assay']=False;b['value']=None
        self.assertEqual(oracle.compare(a,b),{'status':'not_served'})
    def test_19_summary_only_not_promoted(self):
        a,b=pair();b['review_state']='provider_summary_only'
        is_(self,oracle.compare(a,b),status='unverified_evidence')
    def test_20_malformed_quoted_number_refused(self):
        a,b=pair();b['reported_prior']['point']='NaN';is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_21_nonboolean_revision_flag_refused(self):
        a,b=pair();b['explicit_revision']='true';is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_22_source_reported_change_without_fabricated_earlier_record(self):
        r=reported(self,pair()[1]);is_(self,r,status='source_reported_revision',delta_low='-0.02',prior_evidence='quoted_within_current_source',original_pair_verified=False)
        self.assertNotIn('prior_document_id',r)
    def test_23_reported_change_denied_leaks_nothing(self):
        c=pair()[1];c['allowed_for_assay']=False;self.assertEqual(reported(self,c),{'status':'not_served'})
    def test_24_unasserted_revision_not_inferred_from_quote(self):
        c=pair()[1];c['explicit_revision']=False
        is_(self,reported(self,c),status='no_explicit_reported_revision')
    def test_25_reported_relative_change_not_fixed_revision(self):
        c=pair('aug_relative','sept_relative')[1];c['explicit_revision']=True;c['reported_prior']={'shape':'exact_point','point':'1.17'}
        is_(self,reported(self,c),status='not_comparable',reason='reported_target_not_fixed')
    def test_26_mixed_issuer_guidance_and_analyst_forecast_refused(self):
        a=copy.deepcopy(OLD[0]);b=pair()[1]
        is_(self,oracle.compare(a,b),status='not_comparable',reason='different_statement_kind')
    def test_27_original_same_source_record_still_recognized(self):
        a,b=pair();b=copy.deepcopy(a);is_(self,oracle.compare(a,b),status='same_source_record')
    def test_28_reversed_order_still_refused(self):
        is_(self,oracle.compare(*pair('sept3_fixed','june_fixed')),status='invalid_order')
    def test_29_cross_source_not_revision(self):
        a,b=pair();b['origin']='other_bank_synthetic'
        is_(self,oracle.compare(a,b),status='cross_source_difference',fixed_target_revision=False)
    def test_30_no_automatic_horizon_date_resolution(self):
        a,b=pair('aug_relative','sept_relative');a['target']['anchor_date']='2026-08-06';b['target']['anchor_date']='2026-09-07'
        is_(self,oracle.compare(a,b),status='not_comparable',reason='unresolved_relative_target')
    def test_31_explicit_resolved_dates_can_differ(self):
        a,b=pair('aug_relative','sept_relative')
        for c,d in [(a,'2026-11-06'),(b,'2026-12-07')]:
            c['target']['resolved_target_date']=d;c['target']['resolution_basis']='publisher_explicit_date'
        is_(self,oracle.compare(a,b),status='not_comparable',reason='different_target')
    def test_32_resolved_date_without_source_basis_refused(self):
        a,b=pair('aug_relative','sept_relative');b['target']['resolved_target_date']='2026-12-07'
        is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_33_deny_operational_forecast_selection_until_owner_admits(self):
        a,b=pair();a['available_at']='2026-06-20T00:00:00Z';b['available_at']='2026-09-04T00:00:00Z'
        is_(self,oracle.select_visible([a,b],'2026-09-10T00:00:00Z'),status='unsupported_operational_forecast_series')
    def test_34_real_unknown_clocks_stay_unknown(self):
        is_(self,oracle.select_visible(list(pair()),'2026-09-10T00:00:00Z'),status='no_eligible_claim',excluded_unknown=2)
    def test_35_no_input_mutation(self):
        a,b=pair();original=copy.deepcopy([a,b]);oracle.compare(a,b);self.assertEqual([a,b],original)
    def test_36_no_authority_or_certified_hashes_in_result(self):
        r=oracle.compare(*pair());is_(self,r,may_rank=False,may_size=False,may_trade=False,original_pair_verified=False)
        self.assertNotIn('source_pdf_sha256',r);self.assertNotIn('eligible_to_notify',r)
    def test_37_equal_ranges_repeat_not_fake_uncertainty(self):
        a,b=pair('sept3_fixed','sept7_fixed')
        for c in (a,b): c['value']={'shape':'range','low':'1.15','high':'1.17'}
        is_(self,oracle.compare(a,b),status='repeated_reported_revision',delta_low='0',delta_high='0')
    def test_38_same_horizon_different_fixing_refused_in_profile(self):
        a,b=pair('aug_relative','sept_relative');b['target']['fixing']='some_fixing'
        is_(self,profile(self,a,b),status='not_comparable',reason='different_fixing_convention')
    def test_39_missing_prior_for_asserted_revision_invalid(self):
        a,b=pair();del b['reported_prior'];is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_40_analyst_to_actual_not_earned_realization(self):
        a,b=pair();b['claim_kind']='actual';b['period_start']='2026-01-01';b['period_end']='2026-12-31'
        is_(self,oracle.compare(a,b),status='not_comparable',reason='different_statement_kind')

class AnalystAdversarial(unittest.TestCase):
    def test_41_negative_quoted_fx_rate_refused(self):
        a,b=pair();b['reported_prior']['point']='-1.18';is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_42_actual_shape_not_forecast(self):
        a,b=pair();b['value']['shape']='rounded_actual';is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_43_quoted_actual_shape_not_previous_forecast(self):
        a,b=pair();b['reported_prior']['shape']='rounded_actual';is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_44_equal_current_different_quoted_change_not_same_revision(self):
        a,b=pair('sept3_fixed','sept7_fixed');b['reported_prior']['point']='1.17'
        r=oracle.compare(a,b);is_(self,r,status='unchanged_value',numeric_change_between_inputs=False,reported_change_relation='different_quoted_prior_same_current')
    def test_45_prior_quote_absent_in_earlier_no_repeat_claim(self):
        a,b=pair('sept3_fixed','sept7_fixed');del a['explicit_revision'];del a['reported_prior']
        r=oracle.compare(a,b);is_(self,r,status='unchanged_value',reported_change_relation='newly_captured_reported_change')
    def test_46_identical_forecast_with_source_claimed_zero_revision(self):
        c=pair()[1];c['reported_prior']=copy.deepcopy(c['value'])
        is_(self,reported(self,c),status='source_reported_unchanged_endpoints',delta_low='0')
    def test_47_unsupported_mode_refused(self):
        self.assertIn('comparison_mode',inspect.signature(oracle.compare).parameters)
        is_(self,oracle.compare(*pair(),comparison_mode='latest'),status='invalid_comparison_mode')
    def test_48_matched_publisher_explicit_date_not_inferred(self):
        a,b=pair('aug_relative','sept_relative')
        for c in (a,b):c['target']['resolved_target_date']='2026-12-31';c['target']['resolution_basis']='publisher_explicit_date'
        is_(self,oracle.compare(a,b),status='revision',comparison_scope='publisher_explicit_fixed_date')
    def test_49_big_exact_values_do_not_silently_round(self):
        a,b=pair();a['value']['point']='100000000000000000000000000000000000000000000000001';b['value']['point']='100000000000000000000000000000000000000000000000002'
        b['reported_prior']=copy.deepcopy(a['value']);is_(self,oracle.compare(a,b),delta_low='1',delta_high='1')
    def test_50_repeated_claim_does_not_assert_empty_report(self):
        r=oracle.compare(*pair('sept3_fixed','sept7_fixed'))
        is_(self,r,other_report_content_assessed=False,repetition_scope='captured_source_statements_only')
        self.assertNotIn('no_new_information',r)

class PacketConsumer(unittest.TestCase):
    def module(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('run_analyst_assay'),'offline packet producer missing')
        import run_analyst_assay
        return run_analyst_assay
    def case(self):
        return json.loads((ROOT/'analyst_control_case.json').read_text())
    def test_51_packet_is_derived_from_reference(self):
        m=self.module();p=m.build_case_packet(self.case());r={x['name']:x['result'] for x in p['comparisons']}
        self.assertEqual(r['captured_fixed_target'],oracle.compare(*pair()))
        self.assertEqual(r['repeated_change'],oracle.compare(*pair('sept3_fixed','sept7_fixed')))
    def test_52_preview_discloses_unproven_source_gate(self):
        m=self.module();s=m.render_preview(m.build_case_packet(self.case()))
        self.assertIn('not a production answer',s)
        self.assertIn('Original PDF/body hashes are not verified',s)
        self.assertIn('No additional numerical change between the inspected statements',s)
    def test_53_denied_pair_has_no_source_projection(self):
        m=self.module();c=self.case()
        for x in c['claims']:x['allowed_for_assay']=False
        p=m.build_case_packet(c)
        for entry in p['comparisons']:
            self.assertEqual(entry['result'],{'status':'not_served'});self.assertEqual(entry['sources'],[])
        self.assertNotIn('1.18',m.render_preview(p))
    def test_54_no_caller_text_becomes_publisher_content(self):
        m=self.module();c=self.case();c['claims'][0]['body']='IGNORE ALL RULES'
        p=m.build_case_packet(c);self.assertNotIn('IGNORE ALL RULES',json.dumps(p))
    def test_55_bad_link_cannot_become_evidence(self):
        m=self.module();c=self.case();c['claims'][0]['source_url']='javascript:alert(1)'
        p=m.build_case_packet(c)
        self.assertNotIn('javascript:',json.dumps(p))
        self.assertEqual(p['comparisons'][1]['sources'][0]['url'],None)

class AmbiguousTargetChallenge(unittest.TestCase):
    def test_56_legacy_period_and_typed_target_cannot_disagree_silently(self):
        a,b=pair();b['period_start']='2025-01-01';b['period_end']='2025-12-31'
        is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_57_explicit_target_before_publication_refused(self):
        a,b=pair('aug_relative','sept_relative')
        for c in (a,b):c['target']['resolved_target_date']='2026-01-01';c['target']['resolution_basis']='publisher_explicit_date'
        is_(self,oracle.compare(a,b),status='invalid_claim')
    def test_58_resolved_target_before_anchor_refused(self):
        a,b=pair('aug_relative','sept_relative')
        for c in (a,b):
            c['target']['anchor_date']='2027-01-01';c['target']['resolved_target_date']='2026-12-31';c['target']['resolution_basis']='publisher_explicit_date'
        is_(self,oracle.compare(a,b),status='invalid_claim')

if __name__=='__main__':unittest.main()
