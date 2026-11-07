"""Synthetic clustered-loss size/power diagnostic; no market or outcome data.

The design is fixed in research/grey_deer/ew_completion_20261031/power/
EW_POWER_DESIGN_DIAGNOSTIC_2026-11-06.md. The existing scorecard owns all
bootstrap and comparison arithmetic. This runner is NOT the registered power
artifact or full reader; it cannot activate a forecast, fit, ledger or policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine import risk_radar_scorecard as scorecard  # noqa: E402

DESIGN_ID = "grey_deer_ew_clustered_loss_power_diagnostic.v1"
DESIGN_PATH = "research/grey_deer/ew_completion_20261031/power/EW_POWER_DESIGN_DIAGNOSTIC_2026-11-06.md"
PREREG_PATH = "research/grey_deer/ew_completion_20261031/EW_FORECAST_PREREG_v1_2026-10-31.md"
OUTPUT_NAME = "EW_POWER_DESIGN_DIAGNOSTIC_v1.json"
FAMILIES = {
    "grey_deer_ew_mkt_v1": ("M0", "B1"),
    "grey_deer_ew_rs_v1": ("B1_RS", "B2_RS"),
}
N = 200
HORIZON = 21
DRAWS = 2000
MIN_REPLICATIONS = 400
MAX_REPLICATIONS = 1000
PREVALENCE = 0.1
CANDIDATE_AMPLITUDE = 0.03
SKILL_FRACTION = 0.05
BASE_LOSS = PREVALENCE * (1 - PREVALENCE)
COMPARATOR_AMPLITUDE = math.sqrt((BASE_LOSS + CANDIDATE_AMPLITUDE ** 2) / (1 - SKILL_FRACTION) - BASE_LOSS)
ALPHA = 0.05 / 6


def _sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode("ascii")).hexdigest()


def _rng(family: str, replication: int, stream: str) -> random.Random:
    token = f"{DESIGN_ID}|{family}|{replication}|{stream}".encode("ascii")
    return random.Random(int.from_bytes(hashlib.sha256(token).digest(), "big"))


def _signs(family: str, replication: int, stream: str) -> list[int]:
    rng = _rng(family, replication, stream)
    offset = rng.randrange(HORIZON)
    signs = [rng.choice((-1, 1)) for _ in range(math.ceil((N + offset) / HORIZON))]
    return [signs[(index + offset) // HORIZON] for index in range(N)]


def sample(family: str, replication: int) -> dict:
    """Fixed-label-count clustered sample and independent block-noise forecasts.

    Neither candidate nor comparator construction reads the generated outcomes.
    Null and alternative reuse signs and labels, changing candidate amplitude
    only. Expected Brier skill is derived from the design, never selected by
    observing the realized finite sample.
    """
    if family not in FAMILIES or type(replication) is not int or not 0 <= replication < MAX_REPLICATIONS:
        raise ValueError("declared_family_and_replication_required")
    rng = _rng(family, replication, "labels")
    outcomes = [0] * N
    for cluster in range(5):
        start = 12 + 40 * cluster + rng.randint(-5, 5)
        outcomes[start:start+4] = [1] * 4
    candidate_signs = _signs(family, replication, "candidate")
    comparators = {name: [PREVALENCE + COMPARATOR_AMPLITUDE * z
                          for z in _signs(family, replication, "comparator:" + name)]
                   for name in FAMILIES[family]}
    null = [PREVALENCE + COMPARATOR_AMPLITUDE * z for z in candidate_signs]
    alternative = [PREVALENCE + CANDIDATE_AMPLITUDE * z for z in candidate_signs]
    clusters = scorecard._event_cluster_count([(None, None, y) for y in outcomes], HORIZON)
    positive_indices = [i for i, y in enumerate(outcomes) if y]
    return {"family": family, "replication": replication, "outcomes": outcomes,
            "candidate_null": null, "candidate_alternative": alternative,
            "comparators": comparators, "event_count": sum(outcomes),
            "non_event_count": N-sum(outcomes), "event_clusters": clusters,
            "synthetic_adverse_indices": positive_indices[:12] if family.endswith("rs_v1") else [],
            "expected_candidate_brier": BASE_LOSS + CANDIDATE_AMPLITUDE**2,
            "expected_comparator_brier": BASE_LOSS + COMPARATOR_AMPLITUDE**2,
            "expected_alternative_brier_skill": 1 - (BASE_LOSS + CANDIDATE_AMPLITUDE**2) /
                (BASE_LOSS + COMPARATOR_AMPLITUDE**2)}


def evaluate_condition(value: dict, condition: str) -> dict:
    """Consume original numerical owner, retaining both threshold interpretations."""
    if condition not in ("null", "alternative"):
        raise ValueError("declared_condition_required")
    result = scorecard.ew_paired_brier_statistics(
        value["outcomes"], value["candidate_" + condition], value["comparators"], horizon=HORIZON)
    if result.get("status") != "COMPUTED":
        raise ValueError("synthetic_input_not_computable")
    comparisons = {}
    for name, comparison in result["comparisons"].items():
        check = comparison["finite_draw_checks"]["strict_look"]
        comparisons[name] = {"candidate_brier": comparison["candidate_brier"],
                             "comparator_brier": comparison["comparator_brier"],
                             "mean_delta": comparison["mean_delta"],
                             "tail_fraction": check["tail_fraction"],
                             "upper_bound": check["upper_bound"],
                             "tail_rejected": check["counted_tail_rejected"],
                             "bound_negative": check["interpolated_bound_negative"],
                             "predicates_agree": check["predicates_agree"]}
    tail = all(row["tail_rejected"] for row in comparisons.values())
    bound = all(row["bound_negative"] for row in comparisons.values())
    calibrated = result["calibration"]["contains_zero"]
    return {"condition": condition, "comparisons": comparisons,
            "calibration_interval90": result["calibration"]["interval90"],
            "calibration_contains_zero": calibrated,
            "tail_only_with_calibration": tail and calibrated,
            "bound_only_with_calibration": bound and calibrated,
            "both_with_calibration": tail and bound and calibrated,
            "any_finite_draw_disagreement": any(not row["predicates_agree"] for row in comparisons.values())}


def _wilson(successes: int, count: int) -> list[float]:
    # Monte Carlo uncertainty, not a confidence band on any market probability.
    z = 1.959963984540054
    p = successes / count
    divisor = 1 + z*z/count
    center = (p + z*z/(2*count))/divisor
    radius = z*math.sqrt(p*(1-p)/count + z*z/(4*count*count))/divisor
    # Exact binomial boundary limits avoid roundoff such as 8e-19 at zero.
    return [0. if successes == 0 else max(0., center-radius),
            1. if successes == count else min(1., center+radius)]


def _aggregate(rows: list[dict], condition: str) -> dict:
    values = [row[condition] for row in rows]
    count = len(values)
    flags = ("both_with_calibration", "tail_only_with_calibration",
             "bound_only_with_calibration", "calibration_contains_zero",
             "any_finite_draw_disagreement")
    totals = {flag: sum(row[flag] for row in values) for flag in flags}
    by_comparator = {}
    for name in values[0]["comparisons"]:
        candidate = sum(row["comparisons"][name]["candidate_brier"] for row in values)/count
        baseline = sum(row["comparisons"][name]["comparator_brier"] for row in values)/count
        by_comparator[name] = {"mean_candidate_brier": candidate,
                              "mean_comparator_brier": baseline,
                              "aggregate_brier_skill": 1-candidate/baseline}
    return {"replications": count, "counts": totals,
            "rates": {key: value/count for key, value in totals.items()},
            "both_rate_wilson95": _wilson(totals["both_with_calibration"], count),
            "by_comparator": by_comparator}


def run_diagnostic(replications: int = MIN_REPLICATIONS,
                   progress: Callable[[str, int, int], None] | None = None) -> dict:
    """Pure synthetic computation; never opens a source/price/issue/grade file.

    Small runs are explicitly insufficient. The full run never stops early or
    replaces seeds after seeing results. A diagnostic cannot stand in for the
    separately qualified frozen power artifact, source gates or natural time.
    """
    if type(replications) is not int or not 1 <= replications <= MAX_REPLICATIONS:
        raise ValueError("bounded_replication_count_required")
    families = {}
    for family in FAMILIES:
        rows = []
        for index in range(replications):
            value = sample(family, index)
            if value["event_count"] != 20 or value["event_clusters"] != 5 or value["non_event_count"] != 180:
                raise ValueError("fixed_synthetic_counts_changed")
            rows.append({"replication": index, "sample_sha256": _sha(value),
                         "null": evaluate_condition(value, "null"),
                         "alternative": evaluate_condition(value, "alternative")})
            if progress is not None and ((index+1) % 100 == 0 or index+1 == replications):
                progress(family, index+1, replications)
        size, power = _aggregate(rows, "null"), _aggregate(rows, "alternative")
        families[family] = {"null": size, "alternative": power,
                            "replication_floor_met": replications >= MIN_REPLICATIONS,
                            "power_threshold_met_in_this_design": replications >= MIN_REPLICATIONS and
                                power["rates"]["both_with_calibration"] >= .8,
                            "receipts": rows}
    return {"schema": DESIGN_ID, "status": "SYNTHETIC_DIAGNOSTIC_COMPLETE" if replications >= MIN_REPLICATIONS
                else "INSUFFICIENT_REPLICATIONS",
            "registered_power_artifact": False, "scientific_acceptance": False,
            "source_qualification_checked": False, "maturity_checked": False,
            "market_data_read": False, "outcome_data_read": False, "model_fitted": False,
            "design": {"graded_rows": N, "event_count": 20, "non_event_count": 180, "event_clusters": 5,
                       "conceptual_issued_count": 252, "conceptual_span_days": 300,
                       "conceptual_immature_count": 52, "synthetic_rs_adverse_count": 12,
                       "conceptual_counts_are_real_receipts": False,
                       "bootstrap_draws": DRAWS, "block": HORIZON, "bootstrap_seed": 20261031+HORIZON,
                       "strict_alpha": ALPHA, "power_reference_threshold": .8,
                       "prevalence": PREVALENCE, "candidate_amplitude": CANDIDATE_AMPLITUDE,
                       "comparator_amplitude": COMPARATOR_AMPLITUDE,
                       "expected_brier_skill_fraction": SKILL_FRACTION,
                       "replications_per_family_per_condition": replications,
                       "simulation_law": "independent_rademacher_forecast_noise_in_21_row_blocks"},
            "families": families,
            "limitations": ["conditional_on_declared_loss_dgp", "not_price_path_or_market_model",
                            "no_target_event_validation", "no_source_or_epoch_acceptance",
                            "not_the_registered_EW_POWER_v1_artifact", "no_fitted_or_issued_forecast"],
            "authority": {"can_rank": False, "can_gate": False, "can_size": False,
                          "can_trade": False, "can_validate": False}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replications', type=int, default=MIN_REPLICATIONS)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pre-run-ref', required=True)
    args = parser.parse_args(argv)
    # Refuse a second output identity, accepted frozen artifact, or overwriting.
    if args.output.name != OUTPUT_NAME or args.output.exists() or args.output.is_symlink():
        parser.error('new named diagnostic output required; frozen/previous artifact cannot be overwritten')
    if not args.pre_run_ref.startswith('https://github.com/mastermindx-market-intelligence/macro/'):
        parser.error('source-linked pre-run design reference required')
    source_paths = ['scripts/grey_deer_ew_power_diagnostic.py', 'engine/risk_radar_scorecard.py',
                    'tests/test_risk_radar_scorecard.py', DESIGN_PATH, PREREG_PATH,
                    'scripts/grey_deer_ew_forecast_reader.py']
    before = {rel: hashlib.sha256((REPO_ROOT/rel).read_bytes()).hexdigest() for rel in source_paths}
    def progress(family, completed, total):
        print(json.dumps({'family': family, 'completed': completed, 'total': total}), flush=True)
    result = run_diagnostic(args.replications, progress=progress)
    after = {rel: hashlib.sha256((REPO_ROOT/rel).read_bytes()).hexdigest() for rel in source_paths}
    if before != after:
        raise RuntimeError('source_changed_during_synthetic_run')
    result['source_sha256'] = before
    result['pre_run_design_ref'] = args.pre_run_ref
    result['source_closure_sha256'] = _sha(before)
    encoded = json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+'\n'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as target:
        target.write(encoded)
    print(json.dumps({'status': result['status'], 'output': str(args.output),
                      'sha256': hashlib.sha256(encoded.encode()).hexdigest(),
                      'families': {name: {condition: row[condition]['rates'] for condition in ('null','alternative')}
                                   for name,row in result['families'].items()}}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
