"""ROR-1 metric-definition audit. Published table inputs are historic research evidence,
NOT a new financial backtest and not a recalibrated model."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metric_definition_audit import day_level_false_rate_bounds


class PublishedMetricDefinitionTests(unittest.TestCase):
    def test_reported_0751_equals_false_discovery_share(self):
        m = day_level_false_rate_bounds(
            alert_rate=0.17, precision=0.249,
            event_prevalence_upper=0.1890,
        )
        self.assertAlmostEqual(m["false_discovery_rate"], 0.751, places=6)
        self.assertAlmostEqual(m["false_alerts_per_day"], 0.12767, places=6)

    def test_reported_0751_cannot_be_day_level_fpr(self):
        m = day_level_false_rate_bounds(0.17, 0.249, 0.1890)
        self.assertLess(m["fpr_upper_bound"], 0.17)
        self.assertGreater(m["fpr_lower_bound"], 0.12)
        self.assertFalse(m["fpr_lower_bound"] <= 0.751 <= m["fpr_upper_bound"])

    def test_false_discovery_and_false_positive_are_not_interchangeable(self):
        m = day_level_false_rate_bounds(0.17, 0.249, 0.1890)
        self.assertGreater(m["false_discovery_rate"], m["fpr_upper_bound"])

    def test_input_validation_catches_invalid_populations(self):
        bad = [(1.1,.2,.3),(.1,-.2,.3),(.1,.2,1.0)]
        for r,p,u in bad:
            with self.assertRaises(ValueError):
                day_level_false_rate_bounds(r,p,u)


if __name__ == "__main__":
    unittest.main()
