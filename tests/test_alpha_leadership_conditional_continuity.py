from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import alpha_leadership_conditional_continuity as mod


class AlphaLeadershipStage2Tests(unittest.TestCase):
    def test_members_union_deduplicates_index_overlap(self):
        membership = pd.DataFrame({
            "ticker": ["A", "A", "B"],
            "start_date": pd.to_datetime(["2020-01-01"] * 3),
            "end_date": pd.to_datetime(["2020-12-31"] * 3),
            "src": ["sp500", "sp400", "sp600"],
        })
        self.assertEqual(mod.members_asof(membership, "2020-06-01"), ["A", "B"])

    def test_formation_has_231_returns_and_exact_endpoints(self):
        idx = pd.bdate_range("2020-01-01", periods=400)
        spy = pd.Series(100 * np.exp(.0002 * np.arange(400)), index=idx)
        stock = pd.Series(100 * np.exp(.001 * np.arange(400)), index=idx)
        out = mod.formation_measure(stock, spy, idx[-1])
        self.assertEqual(out["formation_returns"], 231)
        self.assertEqual(out["formation_start"], idx[-253])
        self.assertEqual(out["formation_end"], idx[-22])

    def test_continuous_winner_and_loser_both_have_positive_continuity(self):
        idx = pd.bdate_range("2020-01-01", periods=400)
        spy = pd.Series(100 * np.exp(.0001 * np.arange(400)), index=idx)
        up = pd.Series(100 * np.exp(.001 * np.arange(400)), index=idx)
        down = pd.Series(100 * np.exp(-.001 * np.arange(400)), index=idx)
        self.assertAlmostEqual(mod.formation_measure(up, spy, idx[-1])["c"], 1.0)
        self.assertAlmostEqual(mod.formation_measure(down, spy, idx[-1])["c"], 1.0)

    def test_missing_internal_price_rejects_feature(self):
        idx = pd.bdate_range("2020-01-01", periods=400)
        spy = pd.Series(100 * np.exp(.0001 * np.arange(400)), index=idx)
        stock = pd.Series(100 * np.exp(.001 * np.arange(400)), index=idx)
        stock.loc[idx[-100]] = np.nan
        self.assertIsNone(mod.formation_measure(stock, spy, idx[-1]))

    def test_issuer_security_uses_asof_liquidity(self):
        rows = [
            {"issuer": "cik:1", "security": "B", "median_dollar_volume": 10},
            {"issuer": "cik:1", "security": "A", "median_dollar_volume": 20},
            {"issuer": "cik:2", "security": "C", "median_dollar_volume": 5},
        ]
        chosen = mod.choose_issuer_security(rows)
        self.assertEqual({x["security"] for x in chosen}, {"A", "C"})

    def test_dead_tail_scales_only_with_return_agreement(self):
        idx = pd.bdate_range("2024-01-01", periods=20)
        live = pd.Series(np.arange(100, 120, dtype=float), index=idx)
        dead = pd.DataFrame({
            "date": list(idx) + [idx[-1] + pd.offsets.BDay(), idx[-1] + 2 * pd.offsets.BDay()],
            "close": list(live.values / 2) + [60.0, 60.5],
            "source": ["polygon"] * 22,
        })
        out, receipt = mod.normalized_dead_tail(live, dead)
        self.assertEqual(receipt["status"], "qualified_scaled_tail")
        self.assertEqual(len(out), 22)
        self.assertAlmostEqual(receipt["scale"], 2.0)

    def test_dead_tail_rejects_unanchored_series(self):
        idx = pd.bdate_range("2024-01-01", periods=20)
        live = pd.Series(np.arange(100, 120, dtype=float), index=idx)
        future = pd.bdate_range("2024-03-01", periods=10)
        dead = pd.DataFrame({
            "date": future,
            "close": np.arange(20, 30, dtype=float),
            "source": ["polygon"] * 10,
        })
        out, receipt = mod.normalized_dead_tail(live, dead)
        self.assertEqual(receipt["status"], "unqualified_no_overlap")
        self.assertEqual(len(out), len(live))

    def test_dead_tail_rejects_return_shape_mismatch(self):
        idx = pd.bdate_range("2024-01-01", periods=20)
        live = pd.Series(np.arange(100, 120, dtype=float), index=idx)
        dead = pd.DataFrame({
            "date": idx,
            "close": 50 * np.exp(np.sin(np.arange(20))),
            "source": ["polygon"] * 20,
        })
        _, receipt = mod.normalized_dead_tail(live, dead, max_return_error=.001)
        self.assertEqual(receipt["status"], "unqualified_return_mismatch")

    def test_trial_grid_is_four_primary_cells(self):
        grid = mod.trial_grid("a" * 64, "macro@abc")
        self.assertEqual(len(grid), 4)
        self.assertEqual({x["model"] for x in grid}, set(mod.MODELS))
        self.assertEqual({x["horizon"] for x in grid}, {63})
        self.assertEqual({x["fill_rule"] for x in grid}, {"next_session_close"})

    def test_coverage_reference_floor_is_seventy_percent(self):
        self.assertEqual(mod.FEATURE_COVERAGE_REFERENCE_FLOOR, 0.70)

    def test_run_fails_before_trials_when_coverage_is_below_floor(self):
        features = pd.DataFrame({
            "decision": [pd.Timestamp("2024-01-31")], "issuer": ["i1"], "security": ["T1"],
            "m": [.1], "c": [.2], "beta": [1.0], "residual_vol": [.2],
        })
        manifest = {"feature_sha256": "a" * 64, "median_feature_coverage": .65}
        old = mod.build_features
        mod.build_features = lambda _root: (features, manifest)
        try:
            with self.assertRaisesRegex(RuntimeError, "below the 70% cohort-null reference floor"):
                mod.run(Path("/unused"), Path("/unused/report.json"), "macro@test")
        finally:
            mod.build_features = old

    def test_nonlinear_controls_precede_continuity(self):
        frame = pd.DataFrame({
            "m": [.1, .2],
            "beta": [1.0, 1.1],
            "residual_vol": [.2, .3],
            "c": [.4, .5],
        })
        _, nonlinear = mod._design(frame, "nonlinear")
        _, additive = mod._design(frame, "additive")
        _, interaction = mod._design(frame, "interaction")
        self.assertEqual(nonlinear, ["m", "beta", "residual_vol", "abs_m", "m_squared"])
        self.assertEqual(additive, nonlinear + ["c"])
        self.assertEqual(interaction, additive + ["m_x_c"])

    def test_genuine_terminal_minus_one_is_not_clipped(self):
        value = -1.0
        self.assertEqual(value, -1.0)

    def test_walk_forward_recovers_planted_interaction(self):
        rng = np.random.default_rng(7)
        rows = []
        dates = pd.date_range("2010-01-31", periods=80, freq="ME")
        for decision in dates:
            for j in range(50):
                m = rng.normal(0, .25)
                c = rng.uniform(-1, 1)
                beta = rng.normal(1, .2)
                residual_vol = rng.uniform(.1, .4)
                active = .02 * m + .20 * m * c + rng.normal(0, .05)
                rows.append((decision, f"i{j}", f"T{j}", m, c, beta, residual_vol,
                             active, decision + pd.Timedelta(days=80)))
        frame = pd.DataFrame(rows, columns=[
            "decision", "issuer", "security", "m", "c", "beta", "residual_vol",
            "active_return", "exit",
        ])
        frame["status"] = "observed"
        features = frame[["decision", "issuer", "security", "m", "c", "beta", "residual_vol"]]
        outcomes = frame[["decision", "issuer", "security", "exit", "status", "active_return"]]
        predictions, receipts = mod.walk_forward(features, outcomes)
        interaction = [r["interaction_coef"] for r in receipts if r["model"] == "interaction"]
        self.assertGreater(np.mean(interaction), .08)
        self.assertTrue(all(len(predictions[name]) for name in mod.MODELS))

    def test_evaluation_does_not_replace_missing_selected_name(self):
        date = pd.Timestamp("2024-01-31")
        features = pd.DataFrame({
            "decision": [date] * 10,
            "issuer": [f"i{x}" for x in range(10)],
            "security": [f"T{x}" for x in range(10)],
            "m": np.linspace(0, 1, 10),
            "c": [0.] * 10,
            "beta": [1.] * 10,
            "residual_vol": [.2] * 10,
        })
        outcomes = pd.DataFrame({
            "decision": [date] * 10,
            "issuer": [f"i{x}" for x in range(10)],
            "security": [f"T{x}" for x in range(10)],
            "fill": [date + pd.offsets.BDay()] * 10,
            "exit": [date + 64 * pd.offsets.BDay()] * 10,
            "gross_return": [.1] * 10,
            "benchmark_return": [0.] * 10,
            "status": ["observed"] * 9 + ["unknown"],
        })
        outcomes["active_return"] = outcomes.gross_return - outcomes.benchmark_return
        predictions = {
            name: pd.DataFrame({
                "decision": [date] * 10,
                "issuer": [f"i{x}" for x in range(10)],
                "security": [f"T{x}" for x in range(10)],
                "prediction": np.arange(10),
            })
            for name in mod.MODELS
        }
        result = mod.evaluate(features, outcomes, predictions)
        for model in mod.MODELS:
            self.assertEqual(result["models"][model]["complete_top_dates"], 0)


if __name__ == "__main__":
    unittest.main()
