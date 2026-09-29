# Q09 — Executed mathematical exhibits

**Fictional exact arithmetic; not a native evaluator, model fit, financial experiment, independent review or production implementation.**

Same operation `prophet-frontier-hypotheses-20260926-sol-001` / recovery `prophet-frontier-successor-1-20260928`. Companion to `Q09_REMAINING_OPPORTUNITY_SCIENCE_R1.md`. This source is review evidence in the existing scientific ownership, not a second labeler, registry or prediction engine.

## Actual execution and scope

Command: `python q09_mathematical_checks.py`.

Final result: **22 named checks PASS, 0 FAIL**, Python **3.13.5**. One named check traverses all 1,000 stipulated rational three-interval hazard sequences; another enumerates all 1,024 possible assignments of ten ambiguous binary labels. These are constructed arithmetic cases, not market observations or independent empirical experiments. No PyArrow, pandas, network, native source module, protected outcome, fitted model or bootstrap was used. The final 22-check version supersedes its earlier drafts; counts are not added across revisions.

The report's probabilities and prices are invented examples. Assertions test the declared arithmetic and counterexamples, not whether a forecast predicts real securities. The program writes only its adjacent JSON result. The toy exact-point path helper is NOT a production OHLC labeler. Real data/source/identity/clock rights and future Q09 registration remain external gates. H1 is unchanged.

## Byte identities

| Object | Bytes | SHA256 |
|---|---:|---|
| Q09_REMAINING_OPPORTUNITY_SCIENCE_R1.md | 33164 | `bea7b01dba460db9b5ae68bfdbf93df8d68e2a3479928805fee381f72e517366` |
| q09_mathematical_checks.py | 12691 | `7be31c83a3dce743e9bb1d2828718d8acd2b48251162bac75f67a1900f29f3b8` |
| Q09_MATHEMATICAL_RESULTS.json | 6490 | `08bf1dbe1cc3e9eb57d6968595a8c8e31d687db9541b07042b85dd9b5495a020` |

The following fenced blocks are the actual executed source and JSON output, preserved byte-for-byte. Extract the Python block to the named script in an isolated evidence directory to repeat these mathematical checks; do not install it into a production pipeline.

## q09_mathematical_checks.py

```python
"""Q09 finite-horizon mathematical exhibits. Standard library only.

Fictional probabilities and paths; no market data, trained model, sampler,
production import, native labeler, backtest, or experiment executor.
Run: python q09_mathematical_checks.py
"""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import hashlib
import json
import platform

ZERO, ONE = F(0), F(1)
CAUSES = ('U', 'D', 'X')
CLASSES = (*CAUSES, 'S')


def law(hazards):
    """Exact first-event law from finite discrete conditional hazards."""
    if not hazards:
        raise ValueError('empty horizon')
    survival, cumulative, cells = [ONE], [(ZERO,) * 3], []
    for row in hazards:
        if len(row) != 3 or any(type(x) not in (F, int) for x in row):
            raise ValueError('explicit rational hazards required')
        row = tuple(F(x) for x in row)
        if any(x < 0 for x in row) or sum(row) > 1:
            raise ValueError('invalid hazard simplex')
        cell = tuple(survival[-1] * x for x in row)
        cells.append(cell)
        cumulative.append(tuple(a + b for a, b in zip(cumulative[-1], cell)))
        survival.append(survival[-1] * (1 - sum(row)))
    return survival, cumulative, cells


def brier(p, observed):
    if len(p) != 4 or sum(p) != 1 or any(x < 0 for x in p):
        raise ValueError('invalid class probabilities')
    return sum((x - int(i == observed)) ** 2 for i, x in enumerate(p))


def difference_bounds(p, q, labels):
    """Exact rectangle-completion bounds; same true class for both models.

    `labels` is a list of nonempty possible-class sets at ONE fixed horizon.
    No cross-record or temporal constraints are imposed; additional constraints
    can only narrow these outer bounds. Not a confidence interval.
    """
    if not labels or any(not x or not set(x) <= set(range(4)) for x in labels):
        raise ValueError('valid nonempty label sets required')
    delta = [brier(p, y) - brier(q, y) for y in range(4)]
    n = len(labels)
    return (sum(min(delta[y] for y in ys) for ys in labels) / n,
            sum(max(delta[y] for y in ys) for ys in labels) / n)


def incidence_bounds(labels, cause):
    n = len(labels)
    return (F(sum(ys == {cause} for ys in labels), n),
            F(sum(cause in ys for ys in labels), n))


def point_path_event(points, lower=95, upper=110):
    """Toy exact ordered observations only, not an OHLC/native bar labeler."""
    for t, x in enumerate(points[1:], 1):
        if x >= upper:
            return 'U', t
        if x <= lower:
            return 'D', t
    return 'S', len(points) - 1


def landmark_survival_condition(survival, cumulative, s, u):
    if survival[s] == 0:
        raise ValueError('no event-free risk set')
    return tuple((cumulative[s + u][k] - cumulative[s][k]) / survival[s]
                 for k in range(3)) + (survival[s + u] / survival[s],)


checks = []
results = {}


def check(name, predicate):
    if not predicate:
        raise AssertionError(name)
    checks.append({'name': name, 'status': 'PASS'})


def rejects(call):
    try:
        call()
    except ValueError:
        return True
    return False


# 1: exhaustive exact finite constructions, not empirical observations.
grid = [r for r in product((F(0), F(1, 2), F(1)), repeat=3) if sum(r) <= 1]
sequence_count = 0
for hs in product(grid, repeat=3):
    s, c, cells = law(hs)
    for t in range(4):
        assert sum(c[t]) + s[t] == 1
        if t:
            assert s[t] <= s[t - 1]
            assert all(c[t][k] >= c[t - 1][k] for k in range(3))
    # Direct product expression independently recomputes each event-time cell.
    for t in range(3):
        prefix = ONE
        for v in range(t):
            prefix *= 1 - sum(hs[v])
        assert tuple(prefix * hs[t][k] for k in range(3)) == cells[t]
    sequence_count += 1
check('01_simplex_and_time_coherence_exhaustive', sequence_count == 1000)
results['exact_hazard_sequences_checked'] = sequence_count

check('02_negative_or_excess_hazards_rejected',
      rejects(lambda: law([(F(-1, 10), 0, 0)])) and
      rejects(lambda: law([(F(4, 5), F(3, 5), 0)])))
check('03_missing_hazard_is_not_zero', rejects(lambda: law([(None, 0, 0)])))

# 100 fictional origins: 60 lower-first at t1; 20 upper-first at t2; 20 neither.
s, c, _ = law([(0, F(3, 5), 0), (F(1, 2), 0, 0)])
naive_km_upper = F(20, 40)
check('04_competing_risk_censoring_counterexample',
      c[-1] == (F(1, 5), F(3, 5), 0) and naive_km_upper == F(1, 2))
results['competing_risk_example'] = {
    'origins': 100, 'target_first': 20, 'lower_first': 60, 'neither': 20,
    'actual_target_probability': c[-1][0], 'censor_competitors_estimate': naive_km_upper}

s3, c3, cells3 = law([(F(1, 10), F(1, 5), 0)] * 3)
check('05_no_event_mass_not_renormalized',
      c3[-1] == (F(219, 1000), F(438, 1000), 0) and s3[-1] == F(343, 1000))
results['three_step_law'] = dict(zip(CLASSES, (*c3[-1], s3[-1])))
check('06_conditional_target_timing_not_unconditional_median',
      c[-1][0] < F(1, 2) and (2 * F(1, 5)) / F(1, 5) == 2)
results['target_time_example'] = {'conditional_success_time': 2,
                                 'probability_target_by_horizon': F(1, 5),
                                 'unconditional_target_median_within_horizon': None}

cond = landmark_survival_condition(s3, c3, 1, 2)
check('07_landmark_conditioning_preserves_original_law',
      cond == (F(17, 100), F(34, 100), 0, F(49, 100)))
results['remaining_law_after_one_event_free_step'] = dict(zip(CLASSES, cond))
s_dead, c_dead, _ = law([(1, 0, 0), (0, 0, 0)])
check('08_no_rerisk_after_resolved_event',
      rejects(lambda: landmark_survival_condition(s_dead, c_dead, 1, 1)))

path_a, path_b = [100, 94, 111, 108], [100, 111, 94, 108]
check('09_endpoint_equal_first_events_opposite',
      F(path_a[-1], path_a[0]) - 1 == F(path_b[-1], path_b[0]) - 1 == F(2, 25)
      and point_path_event(path_a)[0] == 'D' and point_path_event(path_b)[0] == 'U')
results['endpoint_counterexample'] = {'a': path_a, 'b': path_b, 'both_terminal_return': F(2, 25),
                                     'a_first': 'D', 'b_first': 'U'}

# Same single-bar OHLC: two permitted internal paths, opposite first event.
bar_a, bar_b = [100, 111, 94, 105], [100, 94, 111, 105]
check('10_same_ohlc_first_event_not_identified',
      (bar_a[0], max(bar_a), min(bar_a), bar_a[-1]) ==
      (bar_b[0], max(bar_b), min(bar_b), bar_b[-1]) and
      point_path_event(bar_a)[0] != point_path_event(bar_b)[0])
check('11_gap_in_observation_cannot_certify_later_target_first',
      [path_a[0], path_a[2]] == [path_b[0], path_b[1]] and
      point_path_event(path_a)[0] != point_path_event([100, 111])[0])

labels = [{0}] * 20 + [{1}] * 50 + [{3}] * 20 + [{0, 1}] * 10
check('12_partial_label_incidence_keeps_full_denominator',
      incidence_bounds(labels, 0) == (F(1, 5), F(3, 10)) and
      incidence_bounds(labels, 1) == (F(1, 2), F(3, 5)))
results['partial_label_incidence'] = {'target': incidence_bounds(labels, 0),
                                     'lower': incidence_bounds(labels, 1),
                                     'unresolved_weight': F(1, 10)}
p, q = (F(3, 10), F(1, 2), 0, F(1, 5)), (F(1, 5), F(3, 5), 0, F(1, 5))
lo, hi = difference_bounds(p, q, labels)
known = labels[:90]
known_sum = sum(brier(p, next(iter(y))) - brier(q, next(iter(y))) for y in known)
brute = []
for assignment in product((0, 1), repeat=10):
    brute.append((known_sum + sum(brier(p, y) - brier(q, y) for y in assignment)) / 100)
check('13_paired_brier_bounds_match_all_1024_completions',
      (lo, hi) == (min(brute), max(brute)) == (F(-1, 50), F(1, 50)))
results['brier_difference_bounds_candidate_minus_base'] = (lo, hi)
results['complete_case_brier_difference'] = known_sum / 90
# Separate extremes are valid conservative outer bounds, but may compare
# DIFFERENT truths for the same row and therefore need not be attainable.
independent_lo = sum(min(brier(p, y) for y in ys) - max(brier(q, y) for y in ys)
                     for ys in labels) / 100
independent_hi = sum(max(brier(p, y) for y in ys) - min(brier(q, y) for y in ys)
                     for ys in labels) / 100
check('14_shared_truth_paired_bounds_tighter_than_separate_bounds',
      independent_lo < lo and independent_hi > hi)
results['loose_separate_completion_outer_bounds'] = (independent_lo, independent_hi)

# Properness identity at fixed known truth distribution, no estimated/fitted data.
truth = (F(1, 5), F(3, 5), 0, F(1, 5))
excess = sum(truth[y] * (brier(p, y) - brier(truth, y)) for y in range(4))
check('15_expected_brier_excess_equals_squared_probability_error',
      excess == sum((a - b) ** 2 for a, b in zip(p, truth)) == F(1, 50))

# Rank group is a pre-existing, decision-known variable, NOT chosen from outcomes.
published = (F(3, 5), F(1, 5), 0, F(1, 5))
selected = (F(1, 5), F(3, 5), 0, F(1, 5))  # 20 records: 4,12,0,4
other = (F(7, 10), F(1, 10), 0, F(1, 5))  # 80 records:56,8,0,16
pooled = tuple(F(1, 5) * a + F(4, 5) * b for a, b in zip(selected, other))
check('16_pooled_calibration_not_selected_cohort_calibration',
      pooled == published and published[0] - selected[0] == F(2, 5))
results['selection_calibration_example'] = {'all_predicted_target': F(3, 5),
    'pooled_actual_target': pooled[0], 'selected_actual_target': selected[0],
    'selected_fraction': F(1, 5), 'selected_calibration_gap': F(2, 5)}

# Same first-event distribution, assumed conditional endpoint means differ.
fixed_part = F(1, 5) * F(1, 10) + F(3, 5) * F(-1, 20)
ev_lo, ev_hi = fixed_part + F(1, 5) * F(-1, 25), fixed_part + F(1, 5) * F(2, 25)
check('17_first_event_probabilities_do_not_determine_return',
      (ev_lo, ev_hi) == (F(-9, 500), F(3, 500)))
results['same_event_law_different_assumed_endpoint_expectation'] = (ev_lo, ev_hi)
check('18_censoring_at_one_is_not_complete_no_event_at_three', s3[1] == F(7, 10) and s3[1] != s3[3])
# Even equal marginals do not identify the joint event relevant to a fill policy.
# Cells are (fill+upper, fill+not-upper, no-fill+upper, no-fill+not-upper).
world_a = (F(1, 5), F(3, 10), 0, F(1, 2))
world_b = (0, F(1, 2), F(1, 5), F(3, 10))
check('19_entry_condition_cannot_be_multiplied_by_unrelated_success_forecast',
      sum(world_a) == sum(world_b) == 1 and
      world_a[0] + world_a[1] == world_b[0] + world_b[1] == F(1, 2) and
      world_a[0] + world_a[2] == world_b[0] + world_b[2] == F(1, 5) and
      world_a[0] == F(1, 5) and world_b[0] == 0 and
      F(1, 2) * F(1, 5) != world_a[0] and F(1, 2) * F(1, 5) != world_b[0])
results['equal_marginals_different_fill_target_joint'] = {
    'fill_probability_both': F(1, 2), 'upper_probability_both': F(1, 5),
    'joint_world_a': world_a[0], 'joint_world_b': world_b[0],
    'unjustified_independence_product': F(1, 10)}
check('20_restricted_resolution_duration_includes_every_origin',
      sum(s3[:3]) == F(219, 100))
results['restricted_mean_any_resolution_time_h3'] = sum(s3[:3])



# Identification-width contribution of each uncertain label, not a trading signal.
per_ambiguous_width = (max(brier(p, y) - brier(q, y) for y in (0, 1))
                       - min(brier(p, y) - brier(q, y) for y in (0, 1))) / 100
check('21_label_information_width_is_exactly_additive',
      per_ambiguous_width == F(1, 250) and 10 * per_ambiguous_width == hi - lo)
results['one_ambiguous_row_identification_width'] = per_ambiguous_width
# Each horizon may be on a simplex and still fail to form a valid time curve.
at_one, at_two = (F(3,5),F(1,10),0,F(3,10)), (F(1,2),F(3,10),0,F(1,5))
check('22_per_horizon_normalization_does_not_ensure_time_coherence',
      sum(at_one) == sum(at_two) == 1 and at_two[0] < at_one[0])


def encode(x):
    if isinstance(x, F):
        return {'exact': str(x), 'decimal': float(x)}
    if isinstance(x, dict):
        return {k: encode(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [encode(v) for v in x]
    return x

payload = {
    'kind': 'fictional_exact_math_review_not_empirical_trial',
    'python': platform.python_version(),
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'passed': len(checks), 'failed': 0, 'checks': checks,
    'results': encode(results),
    'market_data_read': False, 'model_fit': False, 'native_test': False,
    'bootstrap': False, 'source_or_production_modified': False,
}
output = Path(__file__).with_name('Q09_MATHEMATICAL_RESULTS.json')
output.write_text(json.dumps(payload, indent=2) + '\n')
print(json.dumps({'passed': len(checks), 'failed': 0,
                  'hazard_sequences': sequence_count,
                  'paired_label_completions': len(brute),
                  'results_path': str(output)}))
```

## Q09_MATHEMATICAL_RESULTS.json

```json
{
  "kind": "fictional_exact_math_review_not_empirical_trial",
  "python": "3.13.5",
  "script_sha256": "7be31c83a3dce743e9bb1d2828718d8acd2b48251162bac75f67a1900f29f3b8",
  "passed": 22,
  "failed": 0,
  "checks": [
    {
      "name": "01_simplex_and_time_coherence_exhaustive",
      "status": "PASS"
    },
    {
      "name": "02_negative_or_excess_hazards_rejected",
      "status": "PASS"
    },
    {
      "name": "03_missing_hazard_is_not_zero",
      "status": "PASS"
    },
    {
      "name": "04_competing_risk_censoring_counterexample",
      "status": "PASS"
    },
    {
      "name": "05_no_event_mass_not_renormalized",
      "status": "PASS"
    },
    {
      "name": "06_conditional_target_timing_not_unconditional_median",
      "status": "PASS"
    },
    {
      "name": "07_landmark_conditioning_preserves_original_law",
      "status": "PASS"
    },
    {
      "name": "08_no_rerisk_after_resolved_event",
      "status": "PASS"
    },
    {
      "name": "09_endpoint_equal_first_events_opposite",
      "status": "PASS"
    },
    {
      "name": "10_same_ohlc_first_event_not_identified",
      "status": "PASS"
    },
    {
      "name": "11_gap_in_observation_cannot_certify_later_target_first",
      "status": "PASS"
    },
    {
      "name": "12_partial_label_incidence_keeps_full_denominator",
      "status": "PASS"
    },
    {
      "name": "13_paired_brier_bounds_match_all_1024_completions",
      "status": "PASS"
    },
    {
      "name": "14_shared_truth_paired_bounds_tighter_than_separate_bounds",
      "status": "PASS"
    },
    {
      "name": "15_expected_brier_excess_equals_squared_probability_error",
      "status": "PASS"
    },
    {
      "name": "16_pooled_calibration_not_selected_cohort_calibration",
      "status": "PASS"
    },
    {
      "name": "17_first_event_probabilities_do_not_determine_return",
      "status": "PASS"
    },
    {
      "name": "18_censoring_at_one_is_not_complete_no_event_at_three",
      "status": "PASS"
    },
    {
      "name": "19_entry_condition_cannot_be_multiplied_by_unrelated_success_forecast",
      "status": "PASS"
    },
    {
      "name": "20_restricted_resolution_duration_includes_every_origin",
      "status": "PASS"
    },
    {
      "name": "21_label_information_width_is_exactly_additive",
      "status": "PASS"
    },
    {
      "name": "22_per_horizon_normalization_does_not_ensure_time_coherence",
      "status": "PASS"
    }
  ],
  "results": {
    "exact_hazard_sequences_checked": 1000,
    "competing_risk_example": {
      "origins": 100,
      "target_first": 20,
      "lower_first": 60,
      "neither": 20,
      "actual_target_probability": {
        "exact": "1/5",
        "decimal": 0.2
      },
      "censor_competitors_estimate": {
        "exact": "1/2",
        "decimal": 0.5
      }
    },
    "three_step_law": {
      "U": {
        "exact": "219/1000",
        "decimal": 0.219
      },
      "D": {
        "exact": "219/500",
        "decimal": 0.438
      },
      "X": {
        "exact": "0",
        "decimal": 0.0
      },
      "S": {
        "exact": "343/1000",
        "decimal": 0.343
      }
    },
    "target_time_example": {
      "conditional_success_time": 2,
      "probability_target_by_horizon": {
        "exact": "1/5",
        "decimal": 0.2
      },
      "unconditional_target_median_within_horizon": null
    },
    "remaining_law_after_one_event_free_step": {
      "U": {
        "exact": "17/100",
        "decimal": 0.17
      },
      "D": {
        "exact": "17/50",
        "decimal": 0.34
      },
      "X": {
        "exact": "0",
        "decimal": 0.0
      },
      "S": {
        "exact": "49/100",
        "decimal": 0.49
      }
    },
    "endpoint_counterexample": {
      "a": [
        100,
        94,
        111,
        108
      ],
      "b": [
        100,
        111,
        94,
        108
      ],
      "both_terminal_return": {
        "exact": "2/25",
        "decimal": 0.08
      },
      "a_first": "D",
      "b_first": "U"
    },
    "partial_label_incidence": {
      "target": [
        {
          "exact": "1/5",
          "decimal": 0.2
        },
        {
          "exact": "3/10",
          "decimal": 0.3
        }
      ],
      "lower": [
        {
          "exact": "1/2",
          "decimal": 0.5
        },
        {
          "exact": "3/5",
          "decimal": 0.6
        }
      ],
      "unresolved_weight": {
        "exact": "1/10",
        "decimal": 0.1
      }
    },
    "brier_difference_bounds_candidate_minus_base": [
      {
        "exact": "-1/50",
        "decimal": -0.02
      },
      {
        "exact": "1/50",
        "decimal": 0.02
      }
    ],
    "complete_case_brier_difference": {
      "exact": "1/150",
      "decimal": 0.006666666666666667
    },
    "loose_separate_completion_outer_bounds": [
      {
        "exact": "-3/50",
        "decimal": -0.06
      },
      {
        "exact": "3/50",
        "decimal": 0.06
      }
    ],
    "selection_calibration_example": {
      "all_predicted_target": {
        "exact": "3/5",
        "decimal": 0.6
      },
      "pooled_actual_target": {
        "exact": "3/5",
        "decimal": 0.6
      },
      "selected_actual_target": {
        "exact": "1/5",
        "decimal": 0.2
      },
      "selected_fraction": {
        "exact": "1/5",
        "decimal": 0.2
      },
      "selected_calibration_gap": {
        "exact": "2/5",
        "decimal": 0.4
      }
    },
    "same_event_law_different_assumed_endpoint_expectation": [
      {
        "exact": "-9/500",
        "decimal": -0.018
      },
      {
        "exact": "3/500",
        "decimal": 0.006
      }
    ],
    "equal_marginals_different_fill_target_joint": {
      "fill_probability_both": {
        "exact": "1/2",
        "decimal": 0.5
      },
      "upper_probability_both": {
        "exact": "1/5",
        "decimal": 0.2
      },
      "joint_world_a": {
        "exact": "1/5",
        "decimal": 0.2
      },
      "joint_world_b": 0,
      "unjustified_independence_product": {
        "exact": "1/10",
        "decimal": 0.1
      }
    },
    "restricted_mean_any_resolution_time_h3": {
      "exact": "219/100",
      "decimal": 2.19
    },
    "one_ambiguous_row_identification_width": {
      "exact": "1/250",
      "decimal": 0.004
    }
  },
  "market_data_read": false,
  "model_fit": false,
  "native_test": false,
  "bootstrap": false,
  "source_or_production_modified": false
}
```
