"""Adversarial C1-M1 checks; no market data or source acquisition."""
import copy
import math
import unittest

import numpy as np

from research.options_estate import market_tide_c1 as c1
from test_market_tide_c1 import synthetic_packet


class ConstantAndClockBoundaries(unittest.TestCase):
    def test_identical_nonzero_continuous_column_is_zero_at_prediction(self):
        # np.std can report floating roundoff for an exactly constant column.
        x = [[math.log(.01), .123456789, .02, 0.]] * 61
        predictions, diag = c1.fit_ridge(x, [7.] * 61, [[10., 8., 9., 0.]])
        self.assertEqual(diag["constant_continuous"], [0, 1, 2])
        self.assertAlmostEqual(predictions[0], 7., places=10)

    def test_completed_close_cannot_be_available_before_its_session_close(self):
        packet = synthetic_packet()
        row = next(r for r in packet["rows"] if r["session"] == "2020-06-15")
        row["source_available_at"] = "2020-06-15T19:59:59Z"
        result = c1.walk_forward(packet, "2022-01-20T00:00:00Z")
        self.assertFalse(any(r["session"] == "2020-06-15" for r in result["predictions"]))

    def test_source_available_at_close_is_not_same_close_execution(self):
        packet = synthetic_packet()
        row = next(r for r in packet["rows"] if r["session"] == "2020-06-15")
        row["source_available_at"] = "2020-06-15T20:00:00Z"
        result = c1.walk_forward(packet, "2022-01-20T00:00:00Z")
        self.assertTrue(any(r["session"] == "2020-06-15" for r in result["predictions"]))
        row["decision_at"] = "2020-06-15T20:00:00Z"
        result = c1.walk_forward(packet, "2022-01-20T00:00:00Z")
        self.assertFalse(any(r["session"] == "2020-06-15" for r in result["predictions"]))

    def test_label_at_training_cutoff_is_not_available_before_cutoff(self):
        packet = synthetic_packet()
        row = next(r for r in packet["rows"] if r["session"] == "2019-12-02")
        row["label_available_at"] = "2020-01-01T00:00:00Z"
        other = copy.deepcopy(packet)
        next(r for r in other["rows"] if r["session"] == "2019-12-02")["y5"] = 99999.
        a, b = [c1.walk_forward(p, "2022-01-20T00:00:00Z") for p in (packet, other)]
        january = lambda out: [r["predictions"] for r in out["predictions"] if r["session"].startswith("2020-01")]
        self.assertEqual(january(a), january(b))
        february = lambda out: [r["predictions"] for r in out["predictions"] if r["session"].startswith("2020-02")]
        self.assertNotEqual(february(a), february(b))

    def test_bootstrap_matches_direct_calendar_index_sampling(self):
        n = 71
        errors = np.column_stack([np.arange(n) / 50 + 1, np.arange(n) / 20 + 2,
                                  np.arange(n) / 30 + 1, np.arange(n) / 80 + .1])
        mask = np.arange(n) % 4 == 0
        actual = c1.block_intervals(errors, mask, block=63)
        rng = np.random.Generator(np.random.PCG64(20260924))
        absolute, relative = [], []
        # Same 2 starts per draw; complete final sample length is 71, not 126.
        for starts in rng.integers(0, n, size=(10000, 2)):
            idx = ((starts[:, None] + np.arange(63)) % n).ravel()[:n]
            selected = errors[idx][mask[idx]]
            delta = np.mean(selected[:, 1] - selected[:, 3])
            absolute.append(delta)
            relative.append(delta / np.mean(selected[:, 1]))
        np.testing.assert_allclose(actual["PEI_vs_P"]["absolute_interval"], np.quantile(absolute, [.0125, .9875]), rtol=1e-12)
        np.testing.assert_allclose(actual["PEI_vs_P"]["relative_interval"], np.quantile(relative, [.0125, .9875]), rtol=1e-12)


class CompleteTrainingYearReview(unittest.TestCase):
    """A full feature roster is not three years of usable training outcomes."""

    @staticmethod
    def run_packet(packet):
        return c1.walk_forward(packet, "2022-01-20T00:00:00Z")

    def test_one_historical_outcome_cannot_certify_three_full_years(self):
        packet = synthetic_packet()
        for row in packet["rows"]:
            if row["session"] < "2020-01-01" and row["session"] != "2019-12-20":
                row.pop("y5")
        result = self.run_packet(packet)
        self.assertEqual(len(result["fits"]), 0)
        self.assertEqual(len(result["predictions"]), 0)

    def test_future_known_outcomes_cannot_certify_full_training_years(self):
        packet = synthetic_packet()
        for row in packet["rows"]:
            if row["session"] < "2020-01-01" and row["session"] != "2019-12-20":
                row["label_available_at"] = "2025-01-01T00:00:00Z"
        self.assertEqual(len(self.run_packet(packet)["fits"]), 0)

    def test_interior_label_gap_invalidates_its_year_not_other_complete_years(self):
        packet = synthetic_packet()
        next(r for r in packet["rows"] if r["session"] == "2018-06-15").pop("y5")
        result = self.run_packet(packet)
        self.assertFalse(any(f["month"].startswith("2020-") for f in result["fits"]))
        first = result["fits"][0]
        self.assertEqual(first["month"], "2021-01")
        self.assertEqual(first["complete_training_years"], [2017, 2019, 2020])

    def test_cutoff_equal_label_does_not_qualify_year_until_next_month(self):
        packet = synthetic_packet()
        next(r for r in packet["rows"] if r["session"] == "2019-12-02")["label_available_at"] = "2020-01-01T00:00:00Z"
        result = self.run_packet(packet)
        self.assertFalse(any(f["month"] == "2020-01" for f in result["fits"]))
        self.assertEqual(result["fits"][0]["month"], "2020-02")
        self.assertEqual(result["fits"][0]["complete_training_years"], [2017, 2018, 2019])

    def test_boundary_purge_does_not_require_unavailable_future_endpoints(self):
        packet = synthetic_packet()
        for row in packet["rows"]:
            if row["session"] < "2020-01-01" <= row["label_end_session"]:
                row.pop("y5")
        result = self.run_packet(packet)
        self.assertEqual(result["fits"][0]["month"], "2020-01")
        self.assertEqual(result["fits"][0]["complete_training_years"], [2017, 2018, 2019])
        # By February those same endpoints are historical, not boundary-purged.
        self.assertFalse(any(f["month"] == "2020-02" for f in result["fits"]))

    def test_genuine_zero_outcomes_remain_eligible(self):
        packet = synthetic_packet()
        for row in packet["rows"]:
            row["y5"] = 0.
        result = self.run_packet(packet)
        self.assertEqual(result["fits"][0]["month"], "2020-01")
        self.assertGreater(result["fits"][0]["n_train"], 700)
        self.assertEqual(result["fits"][0]["reference_mean"], 0.)


if __name__ == "__main__":
    unittest.main()
