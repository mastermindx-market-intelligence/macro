"""Tests for an offline oracle, not the running Mastermind system or parser."""
import copy
import json
from pathlib import Path
import unittest
import revision_oracle as oracle

ROOT = Path(__file__).resolve().parent
REAL = {x['id']: x for x in json.loads((ROOT/'public_control_case.json').read_text())['claims']}

def pair(before='initial', after='revised'):
    return copy.deepcopy(REAL[before]), copy.deepcopy(REAL[after])

def expected(subset, result):
    for key, value in subset.items():
        assert result.get(key) == value, f'{key}: expected {value!r}, got {result.get(key)!r}; result={result!r}'

class RevisionContract(unittest.TestCase):
    def test_01_real_reaffirmation(self):
        expected({'status':'reaffirmation','delta_low':'0','delta_high':'0'}, oracle.compare(*pair('initial','reaffirmed')))
    def test_02_real_point_revision(self):
        expected({'status':'revision','delta_low':'10','delta_high':'10','direction':'higher'},oracle.compare(*pair()))
    def test_03_real_range_revision(self):
        expected({'status':'revision','delta_low':'6','delta_high':'8','midpoint':None},oracle.compare(*pair('revised','range_revision')))
    def test_04_real_actual_is_not_revision(self):
        expected({'status':'realization','actual_position':'inside_stated_range'},oracle.compare(*pair('range_revision','actual_2025')))
    def test_05_real_new_year_is_not_revision(self):
        expected({'status':'not_comparable','reason':'different_period'},oracle.compare(*pair('range_revision','outlook_2026')))
    def test_06_equal_number_not_explicit_reaffirmation(self):
        a,b=pair('initial','reaffirmed');b['explicit_reaffirmation']=False
        expected({'status':'unchanged_value'},oracle.compare(a,b))
    def test_07_different_currency(self):
        a,b=pair();b['currency']='EUR';expected({'status':'not_comparable','reason':'different_currency'},oracle.compare(a,b))
    def test_08_different_scale(self):
        a,b=pair();b['scale']='million';expected({'status':'not_comparable','reason':'different_scale'},oracle.compare(a,b))
    def test_09_different_entity(self):
        a,b=pair();b['entity']='Other issuer [synthetic]';expected({'status':'not_comparable','reason':'different_entity'},oracle.compare(a,b))
    def test_10_different_segment(self):
        a,b=pair();b['scope']='cloud_only';expected({'status':'not_comparable','reason':'different_scope'},oracle.compare(a,b))
    def test_11_different_accounting_basis(self):
        a,b=pair();b['basis']='includes_finance_leases';expected({'status':'not_comparable','reason':'different_basis'},oracle.compare(a,b))
    def test_12_different_scenario(self):
        a,b=pair();b['scenario']='upside';expected({'status':'not_comparable','reason':'different_scenario'},oracle.compare(a,b))
    def test_13_cross_source_not_revision(self):
        a,b=pair();b['origin']='Other issuer analyst [synthetic]';expected({'status':'cross_source_difference'},oracle.compare(a,b))
    def test_14_identical_source_version(self):
        a,b=pair();b=copy.deepcopy(a);expected({'status':'same_source_record'},oracle.compare(a,b))
    def test_15_same_document_amendment_not_new_note(self):
        a,b=pair();b['document_id']=a['document_id'];expected({'status':'source_amendment_requires_review'},oracle.compare(a,b))
    def test_16_reversed_dates(self):
        expected({'status':'invalid_order'},oracle.compare(*pair('revised','initial')))
    def test_17_missing_numeric_value(self):
        a,b=pair();b['value']['point']=None;expected({'status':'invalid_claim'},oracle.compare(a,b))
    def test_18_boolean_is_not_number(self):
        a,b=pair();b['value']['point']=True;expected({'status':'invalid_claim'},oracle.compare(a,b))
    def test_19_float_is_not_source_decimal(self):
        a,b=pair();b['value']['point']=85.0;expected({'status':'invalid_claim'},oracle.compare(a,b))
    def test_20_nonfinite_number(self):
        a,b=pair();b['value']['point']='NaN';expected({'status':'invalid_claim'},oracle.compare(a,b))
    def test_21_reversed_range(self):
        a,b=pair('revised','range_revision');b['value']['low']='95';expected({'status':'invalid_claim'},oracle.compare(a,b))
    def test_22_missing_comparison_key(self):
        a,b=pair();b['scope']='';expected({'status':'incomplete_comparison_key'},oracle.compare(a,b))
    def test_23_permission_is_preflight(self):
        a,b=pair();b['allowed_for_assay']=False;b['value']['point']='NaN'
        self.assertEqual(oracle.compare(a,b),{'status':'not_served'})
    def test_24_unreviewed_source(self):
        a,b=pair();b['review_state']='provider_summary_only';expected({'status':'unverified_evidence'},oracle.compare(a,b))
    def test_25_overlapping_ranges_not_unambiguously_higher(self):
        a,b=pair();a['value']={'shape':'range','low':'75','high':'85'};b['value']={'shape':'range','low':'80','high':'90'}
        expected({'status':'revision','delta_low':'-5','delta_high':'15','direction':'overlap_or_mixed'},oracle.compare(a,b))
    def test_26_no_automatic_midpoint(self):
        out=oracle.compare(*pair('revised','range_revision'));self.assertNotIn('midpoint',out)
    def test_27_approximation_is_preserved(self):
        expected({'approximate_inputs':True},oracle.compare(*pair()))
    def test_28_unknown_availability_is_not_pit(self):
        expected({'status':'no_eligible_claim','excluded_unknown':2},oracle.select_visible(list(pair()),'2025-08-01T00:00:00Z'))
    def test_29_late_acquisition_is_not_earlier_knowledge(self):
        a,b=pair();a['available_at']='2025-02-05T00:00:00Z';b['available_at']='2025-09-01T00:00:00Z'
        expected({'status':'selected','id':'initial'},oracle.select_visible([a,b],'2025-08-01T00:00:00Z'))
    def test_30_old_report_newly_downloaded_does_not_supersede(self):
        a,b=pair();a['available_at']='2025-09-02T00:00:00Z';b['available_at']='2025-07-24T00:00:00Z'
        expected({'status':'selected','id':'revised'},oracle.select_visible([a,b],'2025-09-03T00:00:00Z'))
    def test_31_dependency_invalidation_transitive(self):
        outputs={'comparison':['v1','v2'],'prophet_card':['comparison'],'private_brief':['prophet_card'],'unrelated':['v3']}
        self.assertEqual(oracle.invalidated_outputs(outputs,'v2'),['comparison','private_brief','prophet_card'])
    def test_32_cycle_terminates(self):
        self.assertEqual(oracle.invalidated_outputs({'a':['v1','b'],'b':['a']},'v1'),['a','b'])
    def test_33_raw_labels_do_not_establish_origins(self):
        records=[{'institution_label':'S&T','origin_id':None},{'institution_label':'Goldman Sachs','origin_id':None}]
        expected({'raw_labels':2,'resolved_origins':0,'unresolved_records':2},oracle.source_counts(records))
    def test_34_known_same_origin_is_one(self):
        records=[{'institution_label':'S&T','origin_id':'same-origin'},{'institution_label':'Goldman Sachs','origin_id':'same-origin'}]
        expected({'raw_labels':2,'resolved_origins':1,'unresolved_records':0},oracle.source_counts(records))
    def test_35_input_is_not_mutated(self):
        a,b=pair();old=copy.deepcopy([a,b]);oracle.compare(a,b);self.assertEqual([a,b],old)
    def test_36_no_market_authority(self):
        expected({'authority':'offline_context_only','may_rank':False,'may_size':False,'may_trade':False},oracle.compare(*pair()))
    def test_37_cross_source_difference_is_not_actual_realization(self):
        a,b=pair('range_revision','actual_2025');b['origin']='Other origin [synthetic]';expected({'status':'cross_source_realization_requires_review'},oracle.compare(a,b))
    def test_38_no_evidence_of_full_source_bytes(self):
        self.assertTrue(all(c['source_bytes_hash'] is None and not c['production_source_binding'] for c in REAL.values()))

    def test_39_unchanged_range_has_zero_revision(self):
        a,b=pair('range_revision','range_revision');b['id']='reaffirm_range';b['document_id']='later_doc';b['document_version']='later_version';b['event_date']='2025-11-01';b['explicit_reaffirmation']=True
        expected({'status':'reaffirmation','delta_low':'0','delta_high':'0'},oracle.compare(a,b))
    def test_40_same_day_cross_source_does_not_require_temporal_order(self):
        a,b=pair();b['origin']='Different origin [synthetic]';b['event_date']=a['event_date']
        expected({'status':'cross_source_difference'},oracle.compare(a,b))
    def test_41_precision_change_is_not_numeric_revision(self):
        a,b=pair('initial','reaffirmed');b['explicit_reaffirmation']=False;b['value']['shape']='exact_point'
        expected({'status':'representation_changed','delta_low':'0','delta_high':'0'},oracle.compare(a,b))
    def test_42_same_day_same_source_order_unknown(self):
        a,b=pair();b['event_date']=a['event_date'];expected({'status':'same_day_order_unknown'},oracle.compare(a,b))
    def test_43_zero_baseline_does_not_make_infinite_percent(self):
        a,b=pair();a['value']['point']='0';out=oracle.compare(a,b);self.assertNotIn('percent_low',out)
    def test_44_timezone_required_for_availability_cutoff(self):
        with self.assertRaises(ValueError):oracle.select_visible(list(pair()),'2025-08-01T00:00:00')
    def test_45_mixed_period_series_not_silently_selected(self):
        a,b=pair('range_revision','outlook_2026');a['available_at']='2025-10-30T00:00:00Z';b['available_at']='2026-02-05T00:00:00Z'
        expected({'status':'ambiguous_series'},oracle.select_visible([a,b],'2026-03-01T00:00:00Z'))
    def test_46_actual_quarter_is_not_actual_full_year(self):
        a,b=pair('range_revision','actual_2025');b['period_start']='2025-10-01'
        expected({'status':'not_comparable','reason':'different_period'},oracle.compare(a,b))
    def test_47_unrelated_dependency_is_not_invalidated(self):
        self.assertEqual(oracle.invalidated_outputs({'card':['versionA']},'versionB'),[])
    def test_48_changed_pdf_requires_disclosure(self):
        expected({'status':'source_changed'},oracle.validate_locator({'source_hash':'a'*64,'body_hash':'c'*64,'page':12,'page_count':23},'b'*64))
    def test_49_missing_pdf_hash_is_not_a_verified_locator(self):
        expected({'status':'source_binding_missing'},oracle.validate_locator({'source_hash':None,'body_hash':'c'*64,'page':12,'page_count':23},None))
    def test_50_page_zero_is_invalid(self):
        expected({'status':'invalid_locator'},oracle.validate_locator({'source_hash':'a'*64,'body_hash':'c'*64,'page':0,'page_count':23},'a'*64))
    def test_51_bound_positive_page(self):
        expected({'status':'bound_locator'},oracle.validate_locator({'source_hash':'a'*64,'body_hash':'c'*64,'page':12,'page_count':23},'a'*64))
    def test_52_boolean_page_is_invalid(self):
        expected({'status':'invalid_locator'},oracle.validate_locator({'source_hash':'a'*64,'body_hash':'c'*64,'page':True,'page_count':23},'a'*64))
    def test_53_noncanonical_hash_is_not_normalized(self):
        expected({'status':'source_binding_missing'},oracle.validate_locator({'source_hash':'A'*64,'body_hash':'c'*64,'page':12,'page_count':23},'a'*64))

if __name__=='__main__':
    unittest.main(verbosity=2)
