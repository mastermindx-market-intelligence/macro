"""ROR-1 source-native Risk Radar gate divergence: controlled synthetic observations.

Loads the *actual* Macro owner module, not a transcribed helper.
Nothing is changed in the source worktree or market-data stores.
"""
from __future__ import annotations

import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

MACRO = Path(os.environ.get("ROR1_MACRO_ROOT") or Path(__file__).resolve().parents[3])
sys.path.insert(0, str(MACRO))
from engine import risk_radar as rr  # noqa: E402


def observed_pair(n: int, has_breadth: bool = True, falling: bool = True):
    idx = pd.bdate_range("2025-01-02", periods=n)
    prices = pd.Series(100.0, index=idx)
    prices.iloc[-1] = 80.0 if falling else 120.0
    breadth = pd.DataFrame({"pct_above_200": [45.0] * n}, index=idx) if has_breadth else None
    rank = pd.Series(0.2, index=idx)
    with (
        patch.object(rr, "_s", return_value=prices),
        patch.object(rr.store, "read", return_value=breadth),
        patch.object(rr, "pct_rank_window", return_value=rank),
    ):
        series = rr.context_gate_series(idx)
        live = rr.context_gate_live()
    return bool(series.iloc[-1]), live


class NativeGateParity(unittest.TestCase):
    def test_missing_breadth_opens_replay_but_not_live(self):
        series, live = observed_pair(210, has_breadth=False)
        self.assertTrue(series)
        self.assertTrue(live["spy_below_200dma"])
        self.assertIsNone(live["breadth_weak"])
        self.assertFalse(live["met"])

    def test_warmup_150_bars_opens_replay_but_not_live(self):
        series, live = observed_pair(150, has_breadth=True)
        self.assertTrue(series)
        self.assertIsNone(live["spy_below_200dma"])
        self.assertTrue(live["breadth_weak"])
        self.assertFalse(live["met"])

    def test_210_bars_with_weak_breadth_agrees(self):
        series, live = observed_pair(210, has_breadth=True)
        self.assertTrue(series)
        self.assertTrue(live["met"])
        self.assertTrue(live["spy_below_200dma"])
        self.assertTrue(live["breadth_weak"])

    def test_price_above_200dma_both_closed(self):
        series, live = observed_pair(210, has_breadth=True, falling=False)
        self.assertFalse(series)
        self.assertFalse(live["met"])

    def test_absent_spy_closed_in_both(self):
        idx = pd.bdate_range("2025-01-02", periods=210)
        with patch.object(rr, "_s", return_value=None):
            series = rr.context_gate_series(idx)
            live = rr.context_gate_live()
        self.assertFalse(series.iloc[-1])
        self.assertFalse(live["met"])


if __name__ == "__main__":
    unittest.main()
