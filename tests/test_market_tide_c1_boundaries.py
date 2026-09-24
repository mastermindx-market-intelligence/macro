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


if __name__ == "__main__":
    unittest.main()
