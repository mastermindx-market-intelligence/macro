"""Market Tide C1 pre-market-run measurement checks; stdlib only.
Synthetic outcomes and synthetic price paths. This is not a market backtest,
production scorer, calendar, data reader, forecast, or trading policy.
Run: python market_tide_measurement_checks.py
"""
from math import fsum, isclose, log, sqrt
import json

def main():
    checks = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    # Exact ten-point probability distribution, not a sampled market panel.
    y = [0.0] * 9 + [10.0]
    mean = fsum(y) / len(y)
    mae = lambda x: fsum(abs(v - x) for v in y) / len(y)
    mse = lambda x: fsum((v - x) ** 2 for v in y) / len(y)
    check("mean_equals_one", mean == 1.0)
    check("zero_forecast_mae_equals_one", mae(0) == 1.0)
    check("mean_forecast_mae_equals_1_8", isclose(mae(mean), 1.8))
    check("original_mae_ranks_mean_worse", mae(mean) > mae(0))
    check("zero_forecast_mse_equals_ten", mse(0) == 10.0)
    check("mean_forecast_mse_equals_nine", mse(mean) == 9.0)
    check("amended_mse_ranks_mean_better", mse(mean) < mse(0))
    grid = [i / 10 for i in range(101)]
    check("mean_minimizes_grid_mse", min(grid, key=mse) == 1.0)
    check("median_minimizes_grid_mae", min(grid, key=mae) == 0.0)

    # Scale-invariance discriminator. Each basis may have its own constant.
    structure = [100 * (1.002 ** i) * (1 - .001 * (i % 4))
                 for i in range(64)]
    total_return = [120 * (1.001 ** i) * (1 - .002 * (i % 5))
                    for i in range(69)]
    def features_and_target(s, tr):
        t = 63
        trailing = [log(tr[i] / tr[i-1]) for i in range(t-19, t+1)]
        v20 = sqrt(fsum(r*r for r in trailing) / 20)
        trend = log(s[t] / s[t-63])
        momentum = log(s[t] / s[t-5])
        downside = -min(0.0, *(log(tr[t+k] / tr[t]) for k in range(1, 6)))
        return [v20, trend, momentum, downside / (v20 * sqrt(5))]

    original = features_and_target(structure, total_return)
    check("synthetic_target_is_nonzero", original[-1] > 0)
    scaled = features_and_target([p*.23 for p in structure],
                                 [p*.71 for p in total_return])
    for name, before, after in zip(("v20", "trend63", "momentum5", "Y5"),
                                    original, scaled):
        check("uniform_rescaling_preserves_" + name,
              isclose(before, after, rel_tol=1e-10, abs_tol=1e-12))
    revised = total_return[:]
    revised[-1] *= .7
    changed = features_and_target(structure, revised)
    check("nonuniform_revision_can_change_target",
          not isclose(original[-1], changed[-1], abs_tol=1e-8))
    check("future_target_change_does_not_change_past_features",
          changed[:3] == original[:3])
    print(json.dumps({
        "evidence_type": "synthetic_exact_measurement_checks",
        "market_observations": 0,
        "checks_passed": len(checks),
        "check_names": checks,
        "counterexample": {"mean": mean, "median": 0,
                          "mae_zero": mae(0), "mae_mean": mae(mean),
                          "mse_zero": mse(0), "mse_mean": mse(mean)},
        "amendment": {"identity": "C1-M1",
                      "estimand": "conditional_mean_of_Y5",
                      "primary_score": "mean_squared_error",
                      "naive_baseline": "prior_training_mean",
                      "mae_role": "secondary_nonpromoting_diagnostic"},
        "no_corpus_admission_or_trading_authority": True,
    }, indent=2, allow_nan=False))

if __name__ == "__main__":
    main()
