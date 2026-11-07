"""Test-first offline research examples; no native product imports."""
import unittest
from decimal import Decimal
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
p=Path(__file__).with_name('R15_REVIEW_REFERENCE_CHECKS_2026-09-24.py')
s=spec_from_file_location('r15_checks',p)
m=module_from_spec(s)
s.loader.exec_module(m)

class StreamExamples(unittest.TestCase):
    def test_before_threshold(self):
        r=m.stream_scenario('10000000','produced_silver_oz','0','30')
        self.assertEqual(r['delivered_oz'],'3037500')
        self.assertEqual(r['purchase_payment_usd'],'18225000')
        self.assertEqual(r['contribution_usd'],'72900000')
    def test_after_threshold(self):
        r=m.stream_scenario('10000000','produced_silver_oz','100000000','30')
        self.assertEqual(r['delivered_oz'],'2025000')
        self.assertEqual(r['contribution_usd'],'48600000')
    def test_crossing_threshold(self):
        r=m.stream_scenario('10000000','produced_silver_oz','98987500','30')
        self.assertEqual(r['pre_threshold_delivered_oz'],'1012500')
        self.assertEqual(r['post_threshold_delivered_oz'],'1350000')
        self.assertEqual(r['delivered_oz'],'2362500')
        self.assertEqual(r['contribution_usd'],'56700000')
    def test_payable_not_discounted_twice(self):
        a=m.stream_scenario('10000000','produced_silver_oz','98987500','30')
        b=m.stream_scenario('9000000','payable_silver_oz','98987500','30')
        self.assertEqual(a,b)
    def test_unknown_counter_not_zero(self):
        r=m.stream_scenario('10000000','produced_silver_oz',None,'30')
        self.assertEqual(r,{'status':'not_computed','reason':'unknown_contract_deliveries'})
    def test_missing_basis_refused(self):
        with self.assertRaisesRegex(ValueError,'quantity_basis'):
            m.stream_scenario('10000000','silver','0','30')
    def test_binary_float_input_refused(self):
        with self.assertRaisesRegex(ValueError,'decimal_text'):
            m.stream_scenario(10000000.0,'produced_silver_oz','0','30')
    def test_negative_physical_input_refused(self):
        with self.assertRaisesRegex(ValueError,'nonnegative'):
            m.stream_scenario('-1','produced_silver_oz','0','30')
    def test_nonfinite_input_refused(self):
        with self.assertRaisesRegex(ValueError,'finite'):
            m.stream_scenario('NaN','produced_silver_oz','0','30')
    def test_exact_threshold_reached(self):
        r=m.stream_scenario('3000000','payable_silver_oz','98987500','30')
        self.assertEqual(r['post_threshold_delivered_oz'],'0')
        self.assertEqual(r['ending_contract_deliveries_oz'],'100000000')
    def test_proportional_price_not_valuation(self):
        r=m.stream_scenario('10000000','produced_silver_oz','0','60')
        self.assertEqual(r['contribution_usd'],'145800000')
        self.assertEqual(r['is_valuation'],False)
    def test_zero_not_missing(self):
        r=m.stream_scenario('0','produced_silver_oz','0','30')
        self.assertEqual(r['delivered_oz'],'0')
        self.assertEqual(r['contribution_usd'],'0')

if __name__=='__main__':unittest.main()
