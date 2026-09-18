"""Proposed fixed-grid acceptance tests, not a production evaluator or backtest.
Run against an explicitly supplied source module; expected failures on pinned v1
identify work required by the newly proposed fixed-grid contract. No source edits.
"""
import copy
import importlib.util
import os
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

from engine import yield_momentum as module


def frame(n=100):
    return pd.DataFrame({"us10y": 4.0 + np.arange(n) / 100},
                        index=pd.bdate_range("2025-01-02", periods=n))


def read(f):
    return module.build_yield_momentum(f)["series"]["10y"]


class FixedGridAcceptance(unittest.TestCase):
    def test_complete_grid_five_interval_change(self):
        self.assertEqual(read(frame())["velocity_bp"]["5d"], 5.0)

    def test_missing_middle_does_not_move_five_interval_anchor(self):
        f = frame(); f.iloc[-3, 0] = np.nan
        self.assertEqual(read(f)["velocity_bp"]["5d"], 5.0)

    def test_missing_endpoint_is_not_replaced_by_an_earlier_date(self):
        f = frame(); f.iloc[-6, 0] = np.nan
        self.assertIsNone(read(f)["velocity_bp"]["5d"])

    def test_valid_acceleration_boundaries_survive_missing_middle(self):
        f = frame(); f.iloc[-3, 0] = np.nan
        self.assertEqual(read(f)["acceleration_bp"], 0.0)

    def test_missing_acceleration_boundary_withholds_acceleration(self):
        f = frame(); f.iloc[-23, 0] = np.nan
        self.assertIsNone(read(f)["acceleration_bp"])

    def test_63_interval_endpoints_do_not_require_64_nonnull_rows(self):
        f = frame(64); f.iloc[30, 0] = np.nan
        self.assertEqual(read(f)["velocity_bp"]["63d"], 63.0)

    def test_nonfinite_last_value_is_not_an_available_measurement(self):
        f = frame(); f.iloc[-1, 0] = float("inf")
        self.assertIsNone(read(f)["level"])

    def test_genuinely_observed_flat_values_are_zero_not_unavailable(self):
        f = frame(); f["us10y"] = 4.0
        self.assertEqual(read(f)["velocity_bp"]["5d"], 0.0)

    def test_input_is_not_mutated(self):
        f = frame(); before = f.copy(deep=True)
        read(f)
        pd.testing.assert_frame_equal(f, before)

    def test_missing_latest_stays_stale(self):
        f = frame(); f.iloc[-1, 0] = np.nan
        out = read(f)
        self.assertEqual(out["status"], "stale")
        self.assertIsNone(out["level"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
