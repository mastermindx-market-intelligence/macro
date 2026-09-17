"""New public-source arithmetic/semantic checks; no reader, host or auth tests."""
import copy, json, unittest
from pathlib import Path
from decimal import Decimal
from validate_case import validate, compare_guidance, reconcile, same_basis_total
ROOT=Path(__file__).parent
DATA=json.loads((ROOT/'capex_evidence.json').read_text())
F={x['id']:x for x in DATA['facts']}
class CapexCaseTests(unittest.TestCase):
    def test_primary_fact_pack(self):
        self.assertEqual(validate(DATA),{'sources':5,'facts':26,'publishers':3})
    def test_basis_change_is_not_economic_cut(self):
        r=compare_guidance(F['ms-guide-old'],F['ms-guide-new'])
        self.assertEqual(r['classification'],'measurement_basis_changed')
        self.assertFalse(r['like_for_like'])
        self.assertEqual(r['reported_low_difference'],'-15')
        self.assertIsNone(r['economic_change'])
    def test_range_floor_change_not_uniform_raise(self):
        r=compare_guidance(F['meta-guide-old'],F['meta-guide-new'])
        self.assertEqual(r['classification'],'lower_bound_raised')
        self.assertEqual((r['reported_low_difference'],r['reported_high_difference']),('5','0'))
        self.assertEqual(r['range_width_difference'],'-5')
        self.assertIsNone(r['expected_value_change'])
    def test_guidance_and_actual_not_revision(self):
        b=copy.deepcopy(F['meta-guide-new']);b['kind']='reported_actual'
        with self.assertRaises(ValueError): compare_guidance(F['meta-guide-old'],b)
    def test_different_year_not_revision(self):
        b=copy.deepcopy(F['meta-guide-new']);b['period']='CY2027'
        with self.assertRaises(ValueError): compare_guidance(F['meta-guide-old'],b)
    def test_different_issuer_not_same_source_revision(self):
        b=copy.deepcopy(F['meta-guide-new']);b['issuer']='Microsoft'
        with self.assertRaises(ValueError): compare_guidance(F['meta-guide-old'],b)
    def test_meta_reconciliation(self):
        r=reconcile([F['meta-cfo'],F['meta-ppe'],F['meta-principal']],[1,-1,-1],F['meta-fcf'])
        self.assertEqual(r['calculated'],'784');self.assertTrue(r['matches_reported'])
    def test_amazon_net_ppe(self):
        self.assertTrue(reconcile([F['amzn-ppe-gross'],F['amzn-proceeds']],[1,-1],F['amzn-ppe-net'])['matches_reported'])
    def test_amazon_cash_reconciliation(self):
        r=reconcile([F['amzn-cfo'],F['amzn-ppe-net']],[1,-1],F['amzn-fcf'])
        self.assertEqual(r['calculated'],'-7604');self.assertTrue(r['matches_reported'])
    def test_microsoft_cash_not_total_capex(self):
        self.assertTrue(reconcile([F['ms-cfo'],F['ms-cash-ppe']],[1,-1],F['ms-fcf'])['matches_reported'])
        self.assertFalse(reconcile([F['ms-cfo'],F['ms-quarter-capex']],[1,-1],F['ms-fcf'])['matches_reported'])
    def test_mixed_period_cash_bridge_refused(self):
        with self.assertRaises(ValueError): reconcile([F['meta-cfo-prior'],F['meta-ppe'],F['meta-principal']],[1,-1,-1],F['meta-fcf'])
    def test_cross_company_fcf_total_refused(self):
        # Even after normalizing units and periods, issuer FCF definitions differ.
        a=copy.deepcopy(F['amzn-fcf']);a['period']='2026-Q2'
        with self.assertRaises(ValueError): same_basis_total([F['meta-fcf'],a])
    def test_unknown_is_not_zero(self):
        d=copy.deepcopy(DATA);d['facts'][0]['value']=None
        with self.assertRaises(ValueError): validate(d)
    def test_nonfinite_is_not_number(self):
        d=copy.deepcopy(DATA);d['facts'][0]['value']='NaN'
        with self.assertRaises(ValueError): validate(d)
    def test_no_invalid_ranges(self):
        d=copy.deepcopy(DATA);d['facts'][7]['low']='146'
        with self.assertRaises(ValueError): validate(d)
    def test_no_orphan_source(self):
        d=copy.deepcopy(DATA);d['facts'][0]['source_id']='missing'
        with self.assertRaises(ValueError): validate(d)
if __name__=='__main__':unittest.main()
