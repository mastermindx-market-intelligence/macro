"""Tests of a fixed public-source research replay, not the Mastermind application."""
import importlib.util
import json
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("historical_pilot", HERE / "replay_communications_historical_pilot.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)

class HistoricalPilotTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((HERE / "COMMUNICATIONS_HISTORICAL_INPUT_PILOT_2026-09-24.json").read_text())
    def test_fixed_roster_and_record_counts(self):
        result = pilot.run(self.data)
        self.assertEqual(result.get("income_records"), 16)
        self.assertEqual(result.get("cash_records"), 12)
        self.assertEqual(len(result.get("forecast_diagnostics", [])), 4)
    def test_original_and_later_comparative_are_not_overwritten(self):
        result = pilot.run(self.data)
        self.assertEqual(len(result.get("vintage_checks", [])), 4)
        self.assertTrue(all(r["selected_core_amounts_agree"] for r in result["vintage_checks"]))
        self.assertEqual(len(self.data["income_observations"]), 16)
    def test_2023_comparative_did_not_exist_in_this_sample_in_2023(self):
        self.assertIsNone(pilot.selected_income(self.data, "Meta", 2023, "2023-12-31"))
    def test_date_ceiling_excludes_later_restatement_vintage(self):
        r = pilot.selected_income(self.data, "Meta", 2024, "2024-07-31")
        self.assertEqual(r.get("source_id"), "M24")
    def test_source_period_and_release_year_are_different(self):
        r = pilot.selected_income(self.data, "Meta", 2023, "2024-07-31")
        self.assertEqual(r.get("presentation"), "comparative_in_later_release")
    def test_ttd_cash_is_half_year_less_first_quarter(self):
        q = pilot.quarter_cash(self.data, "The Trade Desk", 2025)
        self.assertEqual(q.get("cfo"), "165013")
        self.assertEqual(q.get("selected_cash_subtotal"), "116695")
        self.assertEqual(len(q.get("input_refs", [])), 2)
    def test_magnite_negative_first_quarter_is_not_clamped(self):
        q = pilot.quarter_cash(self.data, "Magnite", 2024)
        self.assertEqual(q.get("cfo"), "89567")
        self.assertEqual(q.get("selected_cash_subtotal"), "76263")
    def test_meta_lease_payment_included_once(self):
        q = pilot.quarter_cash(self.data, "Meta", 2025)
        self.assertEqual(q.get("selected_cash_subtotal"), "8549")
    def test_alphabet_quarter_cash(self):
        q = pilot.quarter_cash(self.data, "Alphabet", 2025)
        self.assertEqual(q.get("selected_cash_subtotal"), "5301")
    def test_all_four_profit_rises_but_cash_direction_differs(self):
        rows = pilot.run(self.data).get("outcome_comparisons", [])
        self.assertEqual([r["issuer"] for r in rows], self.data["roster"])
        self.assertTrue(all(D(r["operating_income_change"]) > 0 for r in rows))
        self.assertEqual([r["selected_cash_subtotal_direction"] for r in rows], ["down","down","up","down"])
    def test_magnite_historical_slope_is_not_a_valid_marginal_cost_estimate(self):
        rows = pilot.run(self.data).get("forecast_diagnostics", [])
        mg = next(r for r in rows if r["issuer"] == "Magnite")
        self.assertGreater(D(mg["historical_oi_change_per_revenue_change_pct"]), D("700"))
        self.assertAlmostEqual(float(mg["slope_operating_income_prediction"]), 96456.9295, places=3)
        self.assertEqual(mg["actual_operating_income"], "21959")
    def test_decomposition_residual_is_exact_before_formatting(self):
        result = pilot.run(self.data)
        self.assertTrue(result.get("exact_error_decompositions"))
    def test_missing_outcome_retains_four_company_denominator(self):
        d = deepcopy(self.data)
        d["income_observations"] = [r for r in d["income_observations"] if r["id"] != "MG25-income-2025Q2"]
        rows = pilot.run(d).get("forecast_diagnostics", [])
        self.assertEqual(len(rows),4)
        self.assertEqual(rows[-1]["status"],"unavailable")
    def test_missing_half_year_refuses_instead_of_treating_first_quarter_as_q2(self):
        d=deepcopy(self.data)
        d["cash_flow_observations"]=[r for r in d["cash_flow_observations"] if r["id"]!="T25-cash-2025-H1"]
        with self.assertRaisesRegex(ValueError,"cash_inputs_missing"):
            pilot.quarter_cash(d,"The Trade Desk",2025)
    def test_currency_mismatch_is_rejected(self):
        d=deepcopy(self.data); d["cash_flow_observations"][-1]["currency"]="EUR"
        with self.assertRaisesRegex(ValueError,"currency"):
            pilot.validate_pilot(d)
    def test_half_year_period_mismatch_is_rejected(self):
        d=deepcopy(self.data); d["cash_flow_observations"][-1]["period_start"]="2025-04-01"
        with self.assertRaisesRegex(ValueError,"period"):
            pilot.validate_pilot(d)
    def test_duplicated_record_is_rejected(self):
        d=deepcopy(self.data); d["income_observations"].append(deepcopy(d["income_observations"][0]))
        with self.assertRaisesRegex(ValueError,"duplicate"):
            pilot.validate_pilot(d)
    def test_scale_mismatch_is_rejected(self):
        d=deepcopy(self.data); d["income_observations"][0]["units_per_printed_unit"]=1000
        with self.assertRaisesRegex(ValueError,"scale"):
            pilot.validate_pilot(d)
    def test_nonfinite_and_boolean_inputs_are_rejected(self):
        for value in ("NaN", "Infinity", True):
            d=deepcopy(self.data); d["income_observations"][0]["revenue"]=value
            with self.assertRaises(ValueError):
                pilot.validate_pilot(d)
    def test_source_issuer_mismatch_is_rejected(self):
        d=deepcopy(self.data); d["income_observations"][0]["source_id"]="T24"
        with self.assertRaisesRegex(ValueError,"source_issuer"):
            pilot.validate_pilot(d)
    def test_false_native_authority_is_rejected(self):
        d=deepcopy(self.data); d["authority"]["can_rank"]=True
        with self.assertRaisesRegex(ValueError,"authority"):
            pilot.validate_pilot(d)
    def test_same_later_vintage_cannot_change_origin_forecast(self):
        base=pilot.run(self.data)["forecast_diagnostics"][0]
        d=deepcopy(self.data)
        row=next(r for r in d["income_observations"] if r["id"]=="M25-income-2024Q2")
        row["revenue"]="40000"; row["operating_costs_including_cost_of_revenue"]="25153"
        changed=pilot.run(d)["forecast_diagnostics"][0]
        self.assertEqual(base["repeated_growth_revenue_prediction"],changed["repeated_growth_revenue_prediction"])
        self.assertFalse(pilot.run(d)["vintage_checks"][0]["selected_core_amounts_agree"])
    def test_correct_arithmetic_does_not_certify_unseen_source_truth(self):
        d=deepcopy(self.data)
        # A coordinated false transcription remains internally consistent.
        row=next(r for r in d["income_observations"] if r["id"]=="M24-income-2023Q2")
        row["revenue"]="32000"; row["operating_costs_including_cost_of_revenue"]="22608"
        self.assertTrue(pilot.validate_pilot(d))
    def test_working_capital_bridge_is_not_all_of_cfo(self):
        note=pilot.run(self.data).get("magnite_working_capital_diagnostic",{})
        self.assertEqual(note.get("selected_wc_change"),"-81928")
        self.assertEqual(note.get("cfo_change"),"-71039")
        self.assertEqual(note.get("remaining_accounting_change"),"10889")

if __name__ == "__main__":
    unittest.main()
