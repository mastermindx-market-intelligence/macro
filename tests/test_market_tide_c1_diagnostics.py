"""C1 diagnostics: synthetic-only examples, never a market-performance claim."""
from __future__ import annotations

import copy
import importlib
import json
import math
import unittest
from datetime import timedelta

from research.options_estate import market_tide_c1 as core
from test_market_tide_c1 import synthetic_packet

try:
    subject = importlib.import_module("research.options_estate.market_tide_c1_diagnostics")
except ModuleNotFoundError as exc:
    if exc.name != "research.options_estate.market_tide_c1_diagnostics":
        raise
    subject = None


def small_report():
    return {"study": "C1-M1", "evidence_kind": "synthetic", "instrument": "SPY",
            "evaluation_at": "2022-01-20T00:00:00+00:00",
            "primary_cohort_admitted": False, "may_trade": False,
            "can_publish_forecast": False,
            "predictions": [
                {"session": "2020-06-15", "actual": .2, "event_cohort": True,
                 "predictions": {m: .25 for m in core.MODELS}},
                {"session": "2020-06-16", "actual": 1.5, "event_cohort": False,
                 "predictions": {m: 1. for m in core.MODELS}},
                {"session": "2020-06-17", "actual": None, "event_cohort": True,
                 "predictions": {m: 3. for m in core.MODELS}}]}


def path_case():
    packet = synthetic_packet()
    row = next(r for r in packet["rows"] if r["session"] == "2020-06-15")
    days = [r["session"] for r in packet["calendar"]]
    i = days.index(row["session"])
    path = {"basis": "total_return", "price_ref": row["price_ref"],
            "origin_session": row["session"], "origin_close": 100.,
            "origin_available_at": row["source_available_at"], "points": []}
    logs = [-.01, -.03, .02, -.02, .01, -.04, .03, 0., -.02, .01]
    for j, value in enumerate(logs, 1):
        stamp = core.utc(packet["calendar"][i + j]["close_at"])
        path["points"].append({"session": days[i + j],
                               "close": 100 * math.exp(value),
                               "available_at": (stamp + timedelta(minutes=5)).isoformat()})
    row["diagnostic_path"] = path
    report = small_report()
    report["predictions"] = [dict(report["predictions"][0], decision_at=row["decision_at"])]
    return packet, row, report


class Diagnostics(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(subject, "C1 diagnostic consumer is not implemented")

    def test_fixed_risk_band_boundaries(self):
        report = small_report()
        report["predictions"] = [dict(report["predictions"][0], predictions={m: x for m in core.MODELS})
                                 for x in (0., .499, .5, .999, 1., 1.999, 2.)]
        bins = subject.risk_strata(report)["full"]["PEI"]
        self.assertEqual([b["n_issued"] for b in bins], [2, 2, 2, 1])
        self.assertEqual([b["lower_inclusive"] for b in bins], [0., .5, 1., 2.])
        self.assertIsNone(bins[-1]["upper_exclusive"])

    def test_immature_actual_is_counted_not_zero_filled(self):
        bins = subject.risk_strata(small_report())["full"]["P"]
        self.assertEqual(bins[-1]["n_issued"], 1)
        self.assertEqual(bins[-1]["n_scored"], 0)
        self.assertIsNone(bins[-1]["mean_actual"])
        self.assertIsNone(bins[-1]["mean_prediction_scored"])

    def test_risk_band_actual_and_prediction_use_same_mature_rows(self):
        report = small_report()
        report["predictions"][2]["predictions"] = {m: .4 for m in core.MODELS}
        b = subject.risk_strata(report)["full"]["N"][0]
        self.assertEqual((b["n_issued"], b["n_scored"]), (2, 1))
        self.assertAlmostEqual(b["mean_prediction_scored"], .25)
        self.assertAlmostEqual(b["mean_actual"], .2)
        self.assertAlmostEqual(b["mse_descriptive"], .0025)

    def test_event_and_nonevent_bands_are_separate(self):
        d = subject.risk_strata(small_report())
        self.assertEqual(sum(b["n_issued"] for b in d["events"]["P"]), 2)
        self.assertEqual(sum(b["n_issued"] for b in d["non_events"]["P"]), 1)

    def test_band_membership_does_not_depend_on_actuals(self):
        a = small_report(); b = copy.deepcopy(a)
        b["predictions"][0]["actual"] = 100.
        x, y = subject.risk_strata(a), subject.risk_strata(b)
        self.assertEqual([r["n_issued"] for r in x["full"]["P"]],
                         [r["n_issued"] for r in y["full"]["P"]])

    def test_empty_band_means_remain_null(self):
        b = subject.risk_strata(small_report())["events"]["N"][1]
        self.assertEqual(b["n_issued"], 0)
        self.assertIsNone(b["mean_actual"])

    def test_invalid_prediction_rejected(self):
        for value in (True, float("nan"), float("inf"), -.1, "1"):
            report = small_report(); report["predictions"][0]["predictions"]["PEI"] = value
            with self.assertRaises(ValueError): subject.risk_strata(report)

    def test_input_not_mutated(self):
        report = small_report(); old = copy.deepcopy(report)
        subject.risk_strata(report)
        self.assertEqual(old, report)

    def test_horizon_arithmetic_uses_all_intermediate_closes(self):
        packet, row, report = path_case()
        result = subject.horizon_views(packet, report)
        values = result["rows"][0]["horizons"]
        self.assertAlmostEqual(values["3"]["normalized_downside"], .03 / (row["v20"] * math.sqrt(3)))
        self.assertAlmostEqual(values["3"]["signed_log_return"], .02)
        self.assertAlmostEqual(values["3"]["rms_log_return"], math.sqrt((.01**2 + .02**2 + .05**2)/3))
        self.assertAlmostEqual(values["10"]["normalized_downside"], .04 / (row["v20"] * math.sqrt(10)))
        self.assertTrue(result["descriptive_only"])

    def test_each_horizon_has_its_own_maturity(self):
        packet, row, report = path_case()
        report["evaluation_at"] = row["diagnostic_path"]["points"][2]["available_at"]
        h = subject.horizon_views(packet, report)["rows"][0]["horizons"]
        self.assertEqual(h["1"]["status"], "available")
        self.assertEqual(h["3"]["status"], "available")
        self.assertEqual(h["10"]["reason"], "not_mature")

    def test_a_late_intermediate_price_blocks_that_horizon(self):
        packet, row, report = path_case()
        row["diagnostic_path"]["points"][1]["available_at"] = "2023-01-01T00:00:00Z"
        h = subject.horizon_views(packet, report)["rows"][0]["horizons"]
        self.assertEqual(h["1"]["status"], "available")
        self.assertEqual(h["3"]["reason"], "not_mature")

    def test_missing_intermediate_endpoint_is_not_forward_filled(self):
        packet, row, report = path_case()
        del row["diagnostic_path"]["points"][1]
        h = subject.horizon_views(packet, report)["rows"][0]["horizons"]
        self.assertEqual(h["1"]["status"], "available")
        self.assertEqual(h["3"]["reason"], "missing_endpoint")

    def test_path_duplicate_is_ambiguous(self):
        packet, row, report = path_case()
        row["diagnostic_path"]["points"].append(copy.deepcopy(row["diagnostic_path"]["points"][0]))
        h = subject.horizon_views(packet, report)["rows"][0]["horizons"]
        self.assertEqual(h["1"]["reason"], "duplicate_endpoint")

    def test_wrong_price_basis_is_not_relabelled(self):
        packet, row, report = path_case()
        row["diagnostic_path"]["basis"] = "raw"
        h = subject.horizon_views(packet, report)["rows"][0]["horizons"]
        self.assertEqual(h["1"]["reason"], "path_basis_or_identity_mismatch")

    def test_wrong_price_reference_rejected(self):
        packet, row, report = path_case()
        row["diagnostic_path"]["price_ref"] = "another-vintage"
        h = subject.horizon_views(packet, report)["rows"][0]["horizons"]
        self.assertEqual(h["1"]["reason"], "path_basis_or_identity_mismatch")

    def test_origin_cannot_be_first_available_after_decision(self):
        packet, row, report = path_case()
        row["diagnostic_path"]["origin_available_at"] = "2020-06-16T00:00:00Z"
        h = subject.horizon_views(packet, report)["rows"][0]["horizons"]
        self.assertEqual(h["1"]["reason"], "invalid_origin_clock")

    def test_endpoint_available_before_close_rejected(self):
        packet, row, report = path_case()
        row["diagnostic_path"]["points"][0]["available_at"] = "2020-06-16T01:00:00Z"
        h = subject.horizon_views(packet, report)["rows"][0]["horizons"]
        self.assertEqual(h["1"]["reason"], "endpoint_precedes_close")

    def test_invalid_endpoint_number_is_not_zero(self):
        for value in (None, True, -1, 0, float("nan")):
            packet, row, report = path_case(); row["diagnostic_path"]["points"][0]["close"] = value
            h = subject.horizon_views(packet, report)["rows"][0]["horizons"]
            self.assertEqual(h["1"]["status"], "unavailable")

    def test_missing_path_does_not_invent_other_horizons_from_y5(self):
        packet, row, report = path_case(); row.pop("diagnostic_path")
        d = subject.horizon_views(packet, report)
        self.assertEqual(d["horizons"]["1"]["full"]["n_available"], 0)
        self.assertEqual(d["rows"][0]["horizons"]["1"]["reason"], "path_unavailable")

    def test_horizon_empty_means_null_and_no_score(self):
        packet, row, report = path_case(); row.pop("diagnostic_path")
        d = subject.horizon_views(packet, report)["horizons"]["10"]["full"]
        self.assertIsNone(d["mean_signed_log_return"])
        self.assertNotIn("mse", d)

    def test_horizon_input_is_immutable(self):
        packet, row, report = path_case(); before = copy.deepcopy(packet)
        subject.horizon_views(packet, report)
        self.assertEqual(before, packet)

    def test_all_path_values_rescale_without_changing_results(self):
        packet, row, report = path_case()
        before = subject.horizon_views(packet, report)
        row["diagnostic_path"]["origin_close"] *= 11
        for p in row["diagnostic_path"]["points"]: p["close"] *= 11
        after = subject.horizon_views(packet, report)
        for h in ("1", "3", "10"):
            self.assertAlmostEqual(before["rows"][0]["horizons"][h]["normalized_downside"],
                                   after["rows"][0]["horizons"][h]["normalized_downside"])

    def test_cross_instrument_keeps_reports_separate(self):
        a = small_report(); b = copy.deepcopy(a); b["instrument"] = "QQQ"
        joined = subject.compose_reports([a, b])
        self.assertEqual(set(joined["instruments"]), {"SPY", "QQQ"})
        self.assertEqual(joined["missing_instruments"], ["IWM"])
        self.assertIsNone(joined["pooled_score"])
        self.assertFalse(joined["independent_replications"])
        self.assertFalse(joined["may_trade"])

    def test_duplicate_instrument_rejected_not_pooled(self):
        with self.assertRaises(ValueError): subject.compose_reports([small_report(), small_report()])

    def test_mixed_synthetic_and_retrospective_reports_rejected(self):
        a = small_report(); b = copy.deepcopy(a); b.update(instrument="QQQ", evidence_kind="retrospective_supplied")
        with self.assertRaises(ValueError): subject.compose_reports([a, b])

    def test_mismatched_evaluation_times_rejected(self):
        a = small_report(); b = copy.deepcopy(a); b.update(instrument="QQQ", evaluation_at="2022-01-21T00:00:00Z")
        with self.assertRaises(ValueError): subject.compose_reports([a, b])

    def test_composition_does_not_copy_granted_authority(self):
        a = small_report(); a["may_trade"] = True
        with self.assertRaises(ValueError): subject.compose_reports([a])

    def test_diagnostic_wrapper_preserves_all_primary_predictions_and_scores(self):
        packet = synthetic_packet(); before = copy.deepcopy(packet)
        original = core.walk_forward(packet, "2022-01-20T00:00:00Z")
        scores = core.summarize(original)
        new = subject.analyze_packet(packet, "2022-01-20T00:00:00Z")
        self.assertEqual(new["predictions"], original["predictions"])
        self.assertEqual(new["fits"], original["fits"])
        for name, value in scores.items():
            if name != "not_implemented": self.assertEqual(new["summary"][name], value)
        self.assertEqual(packet, before)
        self.assertFalse(new["primary_cohort_admitted"])
        json.dumps(new, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
