import unittest
from phase_budget import QualificationBudget,BudgetRefused

class RootBudgetTests(unittest.TestCase):
    def test_raw_charge_checks_deadline(self):
        now=[0];b=QualificationBudget(lambda:now[0]);b.begin('cli');now[0]=60
        with self.assertRaises(BudgetRefused):b.charge_raw(0)
        self.assertTrue(b.snapshot().frozen)
    def test_metadata_checks_total_deadline(self):
        now=[0];b=QualificationBudget(lambda:now[0]);now[0]=900
        with self.assertRaises(BudgetRefused):b.charge_metadata(0)
        self.assertTrue(b.snapshot().frozen)
    def test_snapshot_clock_rewind_freezes_and_remains_inspectable(self):
        now=[5];b=QualificationBudget(lambda:now[0]);now[0]=4
        self.assertTrue(b.snapshot().frozen)
        self.assertTrue(b.snapshot().frozen)
    def test_nonboolean_success_latches_uncertain_phase(self):
        b=QualificationBudget(lambda:0);b.begin('cli')
        with self.assertRaises(BudgetRefused):b.finish('cli',1)
        self.assertTrue(b.snapshot().frozen)
        with self.assertRaises(BudgetRefused):b.finish('cli',True)
    def test_huge_clock_is_typed_and_frozen(self):
        now=[0];b=QualificationBudget(lambda:now[0]);now[0]=10**1000
        with self.assertRaises(BudgetRefused):b.begin('cli')
        self.assertTrue(b.snapshot().frozen)

if __name__=='__main__':unittest.main()
