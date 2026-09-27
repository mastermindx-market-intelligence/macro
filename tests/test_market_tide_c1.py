"""C1-M1 research mechanics. All generated observations are SYNTHETIC.

The weekday roster below is a test fixture, NOT an exchange-calendar producer.
Run from the repository root: python -m unittest discover -s tests -p test_market_tide_c1.py
"""
from __future__ import annotations

import copy
import importlib
import json
import math
import unittest
from datetime import date, datetime, timedelta, timezone

import numpy as np

try:
    c1 = importlib.import_module("research.options_estate.market_tide_c1")
except ModuleNotFoundError as exc:
    if exc.name != "research.options_estate.market_tide_c1":
        raise
    c1 = None


def synthetic_packet():
    days = []
    d = date(2017, 1, 1)
    while d <= date(2022, 1, 14):
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    closes = [datetime(d.year, d.month, d.day, 20, tzinfo=timezone.utc) for d in days]
    rows = []
    for i in range(len(days) - 5):
        flags = {key: int(i % period == 0) for key, period in zip(("CPI", "NFP", "FOMC"), (11, 13, 17))}
        rows.append({
            "session": days[i].isoformat(),
            "decision_at": (closes[i] + timedelta(minutes=15)).isoformat(),
            "source_available_at": (closes[i] + timedelta(minutes=5)).isoformat(),
            "event_schedule_known_at": (closes[i] - timedelta(days=2)).isoformat(),
            "price_ref": "synthetic:dual-basis:fixture-v1",
            "event_ref": "synthetic:schedule:fixture-v1",
            "v20": .01 + .001 * (i % 5), "trend63": .05 * math.cos(i / 29),
            "momentum5": .015 * math.sin(i / 7),
            "event_flags": flags,
            "event_times": {key: [(closes[i + 1] - timedelta(hours=6)).isoformat()] if flag else [] for key, flag in flags.items()},
            "y5": .4 + .3 * (1 + math.sin(i / 9)),
            "label_end_session": days[i + 5].isoformat(),
            "label_available_at": (closes[i + 5] + timedelta(minutes=5)).isoformat(),
        })
    return {"study": "C1-M1", "evidence_kind": "synthetic", "instrument": "SPY",
            "calendar_ref": "synthetic:weekday-fixture-not-XNYS",
            "coverage_start": "2017-01-01", "coverage_end": "2022-01-14",
            "calendar": [{"session": d.isoformat(), "close_at": t.isoformat()} for d, t in zip(days, closes)],
            "rows": rows}


class C1Mechanics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if c1 is None:
            raise AssertionError("C1-M1 research runner has not been implemented")
        cls.packet = synthetic_packet()
        cls.result = c1.walk_forward(cls.packet, "2022-01-20T00:00:00Z")

    def test_target_formula_and_preorigin_volatility(self):
        structure = np.exp(np.arange(64) * .001).tolist()
        total = np.exp(np.arange(64) * .002).tolist()
        total += [total[-1] * math.exp(x) for x in (-.01, -.02, .01, -.005, .005)]
        m = c1.measure_closes(structure, total)
        self.assertAlmostEqual(m["v20"], .002)
        self.assertAlmostEqual(m["trend63"], .063)
        self.assertAlmostEqual(m["momentum5"], .005)
        self.assertAlmostEqual(m["y5"], .02 / (.002 * math.sqrt(5)))

    def test_target_cannot_use_four_endpoints(self):
        with self.assertRaises(ValueError):
            c1.measure_closes(list(range(1, 65)), list(range(1, 69)))

    def test_zero_volatility_rejected_without_floor(self):
        with self.assertRaises(ValueError):
            c1.measure_closes([100.] * 64, [100.] * 69)

    def test_bad_price_is_not_filled(self):
        for bad in (0, -1, True, float("nan"), float("inf")):
            prices = list(range(1, 70)); prices[55] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                c1.measure_closes(list(range(1, 65)), prices)

    def test_future_tail_does_not_change_features(self):
        s = np.exp(np.arange(64) * .001).tolist()
        t = np.exp(np.arange(69) * .002).tolist()
        altered = t[:64] + [x * .3 for x in t[64:]]
        a, b = c1.measure_closes(s, t), c1.measure_closes(s, altered)
        for key in ("v20", "trend63", "momentum5"):
            self.assertEqual(a[key], b[key])
        self.assertNotEqual(a["y5"], b["y5"])

    def test_independent_basis_rescaling_invariant(self):
        s = np.exp(np.arange(64) * .001).tolist(); t = np.exp(np.arange(69) * -.002).tolist()
        a, b = c1.measure_closes(s, t), c1.measure_closes([x * 7 for x in s], [x * 3 for x in t])
        for key in a:
            self.assertAlmostEqual(a[key], b[key], places=10)

    def test_locked_nested_feature_sets(self):
        r = copy.deepcopy(self.packet["rows"][0]); r.update(trend63=.1, momentum5=-.01)
        r["event_flags"] = {"CPI": 1, "NFP": 1, "FOMC": 1}
        p, pe, pei = (c1.design(r, name) for name in ("P", "PE", "PEI"))
        self.assertEqual((len(p), len(pe), len(pei)), (4, 7, 9))
        self.assertEqual(p, pe[:4]); self.assertEqual(pe, pei[:7])
        self.assertEqual(p[3], 1); self.assertEqual(pei[-2:], [2, 1])

    def test_no_unregistered_predictor(self):
        r = copy.deepcopy(self.packet["rows"][0]); a = c1.design(r, "PEI")
        r.update(actual=1e9, sentiment=1e9, gex=-1e9)
        self.assertEqual(a, c1.design(r, "PEI"))
        with self.assertRaises(ValueError): c1.design(r, "GEX")

    def test_ridge_mean_penalty_not_sum_penalty(self):
        x = [[-1., 0., 0., 0.], [1., 0., 0., 1.]]; y = [1., 3.]
        a, _ = c1.fit_ridge(x, y, x)
        b, _ = c1.fit_ridge(x * 10, y * 10, x)
        np.testing.assert_allclose(a, b, atol=1e-12)

    def test_intercept_not_penalized(self):
        p, diag = c1.fit_ridge([[0., 0., 0., 0.]] * 5, [7.] * 5, [[99., 0., 0., 0.]])
        self.assertAlmostEqual(p[0], 7.)
        self.assertEqual(diag["constant_continuous"], [0, 1, 2])

    def test_training_only_transform(self):
        x = [[1., 2., 3., 0.], [3., 4., 5., 1.]]
        _, a = c1.fit_ridge(x, [1., 2.], [[100., 100., 100., 0.]])
        _, b = c1.fit_ridge(x, [1., 2.], [[-100., -100., -100., 1.]])
        self.assertEqual(a, b)
        self.assertEqual(a["continuous_mean"], [2., 3., 4.])

    def test_predictions_clipped_at_zero(self):
        p, _ = c1.fit_ridge([[-1., 0., 0., 0.], [1., 0., 0., 0.]], [0., 2.], [[-100., 0., 0., 0.]])
        self.assertEqual(p[0], 0.)

    def test_first_test_year_requires_three_complete_years(self):
        self.assertEqual(self.result["predictions"][0]["session"][:4], "2020")
        self.assertTrue(all(len(f["complete_training_years"]) >= 3 for f in self.result["fits"]))

    def test_monthly_not_daily_refit(self):
        months = {r["session"][:7] for r in self.result["predictions"]}
        self.assertEqual(len(months), len(self.result["fits"]))

    def test_labels_are_mature_and_purged_before_cutoff(self):
        for f in self.result["fits"]:
            self.assertLess(f["last_training_label_at"], f["cutoff_at"])
            self.assertGreater(f["purged_or_immature"], 0)

    def test_future_outcomes_cannot_change_earlier_predictions(self):
        changed = copy.deepcopy(self.packet)
        for r in changed["rows"]:
            if r["session"] >= "2021-01-01": r["y5"] += 100.
        b = c1.walk_forward(changed, "2022-01-20T00:00:00Z")
        before = lambda report: [(r["session"], r["predictions"]) for r in report["predictions"] if r["session"] < "2021-01-01"]
        self.assertEqual(before(self.result), before(b))

    def test_missing_year_is_not_counted_as_complete(self):
        changed = copy.deepcopy(self.packet)
        changed["rows"] = [r for r in changed["rows"] if r["session"] != "2018-06-05"]
        out = c1.walk_forward(changed, "2022-01-20T00:00:00Z")
        self.assertEqual(out["predictions"][0]["session"][:4], "2021")
        self.assertNotIn(2018, out["fits"][0]["complete_training_years"])

    def test_unknown_event_is_not_zero(self):
        changed = copy.deepcopy(self.packet); r = next(r for r in changed["rows"] if r["session"] == "2020-06-15")
        r["event_flags"]["CPI"] = None
        out = c1.walk_forward(changed, "2022-01-20T00:00:00Z")
        self.assertFalse(any(r["session"] == "2020-06-15" for r in out["predictions"]))
        self.assertIn("event_coverage_unavailable", [e["reason"] for e in out["excluded"]])

    def test_unavailable_inputs_never_enter_prediction(self):
        for key, value in (("source_available_at", "2023-01-01T00:00:00Z"), ("event_schedule_known_at", None), ("decision_at", "2020-06-15T20:15:00")):
            changed = copy.deepcopy(self.packet); r = next(r for r in changed["rows"] if r["session"] == "2020-06-15"); r[key] = value
            out = c1.walk_forward(changed, "2022-01-20T00:00:00Z")
            with self.subTest(key=key): self.assertFalse(any(r["session"] == "2020-06-15" for r in out["predictions"]))

    def test_boolean_numeric_input_rejected(self):
        changed = copy.deepcopy(self.packet); r = next(r for r in changed["rows"] if r["session"] == "2020-06-15"); r["v20"] = True
        out = c1.walk_forward(changed, "2022-01-20T00:00:00Z")
        self.assertFalse(any(r["session"] == "2020-06-15" for r in out["predictions"]))

    def test_event_flag_time_disagreement_rejected(self):
        changed = copy.deepcopy(self.packet); r = next(r for r in changed["rows"] if r["session"] == "2020-06-15")
        r["event_flags"]["CPI"] = 1; r["event_times"]["CPI"] = ["2021-01-01T13:30:00Z"]
        out = c1.walk_forward(changed, "2022-01-20T00:00:00Z")
        self.assertFalse(any(r["session"] == "2020-06-15" for r in out["predictions"]))

    def test_wrong_fifth_session_cannot_supply_label(self):
        changed = copy.deepcopy(self.packet); r = next(r for r in changed["rows"] if r["session"] == "2020-06-15")
        r["label_end_session"] = "2020-06-16"
        out = c1.walk_forward(changed, "2022-01-20T00:00:00Z")
        prediction = next(r for r in out["predictions"] if r["session"] == "2020-06-15")
        self.assertIsNone(prediction["actual"])

    def test_duplicate_session_fails_closed(self):
        changed = copy.deepcopy(self.packet); changed["rows"].append(copy.deepcopy(changed["rows"][0]))
        with self.assertRaises(ValueError): c1.walk_forward(changed, "2022-01-20T00:00:00Z")

    def test_out_of_order_input_does_not_change_output(self):
        changed = copy.deepcopy(self.packet); changed["rows"].reverse()
        self.assertEqual(self.result, c1.walk_forward(changed, "2022-01-20T00:00:00Z"))

    def test_input_immutable(self):
        changed = copy.deepcopy(self.packet); before = copy.deepcopy(changed)
        c1.walk_forward(changed, "2022-01-20T00:00:00Z")
        self.assertEqual(changed, before)

    def test_mean_not_median_reference(self):
        first = self.result["fits"][0]
        self.assertAlmostEqual(first["reference_mean"], self.result["predictions"][0]["predictions"]["N"])

    def test_source_flags_cannot_grant_authority(self):
        changed = copy.deepcopy(self.packet); changed.update(source_qualified=True, can_trade=True)
        out = c1.walk_forward(changed, "2022-01-20T00:00:00Z")
        self.assertFalse(out["can_publish_forecast"]); self.assertFalse(out["may_trade"])
        self.assertFalse(out["primary_cohort_admitted"])

    def test_score_uses_squared_error_and_common_rows(self):
        s = c1.score_predictions([0., 2.], {"N": [1., 1.], "P": [0., 1.], "PE": [0., 1.], "PEI": [0., 2.]})
        self.assertEqual(s["models"]["N"]["mse"], 1.)
        self.assertEqual(s["models"]["P"]["mse"], .5)
        self.assertEqual(s["comparisons"]["PEI_vs_P"]["relative_mse_reduction"], 1.)

    def test_zero_reference_mse_is_undefined_relative(self):
        s = c1.score_predictions([0., 0.], {k: [0., 0.] for k in ("N", "P", "PE", "PEI")})
        self.assertIsNone(s["comparisons"]["PEI_vs_P"]["relative_mse_reduction"])

    def test_score_refuses_unpaired_arrays(self):
        with self.assertRaises(ValueError): c1.score_predictions([1., 2.], {k: [0.] for k in ("N", "P", "PE", "PEI")})

    def test_absent_event_cohort_is_not_zero_error(self):
        s = c1.score_predictions([], {k: [] for k in ("N", "P", "PE", "PEI")})
        self.assertIsNone(s["models"]["PEI"]["mse"])

    def test_bootstrap_is_paired_and_seeded(self):
        errors = np.tile([1., 2., 1.5, .5], (130, 1))
        a = c1.block_intervals(errors, [True] * 130, block=63)
        b = c1.block_intervals(errors, [True] * 130, block=63)
        self.assertEqual(a, b)
        self.assertEqual(a["draws"], 10000)
        np.testing.assert_allclose(a["PEI_vs_P"]["absolute_interval"], [1.5, 1.5])

    def test_bootstrap_retains_missing_positions(self):
        e = np.tile([1., 2., 1.5, .5], (130, 1)); mask = np.ones(130, dtype=bool); mask[20:70] = False
        a = c1.block_intervals(e, mask, block=63)
        self.assertEqual(a["calendar_positions"], 130)
        self.assertEqual(a["eligible_positions"], 80)

    def test_bootstrap_empty_event_sample_is_unavailable(self):
        a = c1.block_intervals(np.zeros((70, 4)), [False] * 70, block=63)
        self.assertIsNone(a["PEI_vs_PE"]["absolute_interval"])

    def test_outputs_json_finite(self):
        json.dumps(self.result, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
