#!/usr/bin/env python3
"""Bounded, independently authored review of the frozen matched-controls lab.

No imports or execution of either lab's analysis/validator. Reads the immutable
input matrices and frozen receipts; writes only beside this review script.
The direct graph oracle uses Cartesian products, not either producer algorithm.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
from itertools import combinations, product
from math import ceil, fsum, isclose, isfinite, prod, sqrt
from pathlib import Path
from statistics import fmean, pstdev, stdev
import json
import sys

import numpy as np

OUT = Path(__file__).resolve().parent
DOCKET = OUT.parents[2]
LAB = DOCKET / "deepening_20261009/matched_controls"
SOURCE = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"
CHECKS = []


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def check(label, condition):
    CHECKS.append({"id": label, "status": "PASS" if condition else "FAIL"})
    if not condition:
        raise AssertionError(label)


def near(label, actual, expected, tolerance=2e-11):
    check(label, isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance))


def matrix(value):
    return [dict(zip(value["columns"], row)) for row in value["data"]]


def assignments(neighbors):
    """Each slot-ordered tuple appears once; never deduplicate portfolios."""
    return [a for a in product(*neighbors) if len(set(a)) == len(a)]


def observed(row):
    return (row["status"] == "observed" and row["excess_cc"] is not None
            and isfinite(row["excess_cc"]))


manifest = read(LAB / "MANIFEST.json")
input_hashes = {}
for item in manifest["files"]:
    path = LAB / item["path"]
    check("hash:lab:" + item["path"], digest(path) == item["sha256"])
    check("bytes:lab:" + item["path"], path.stat().st_size == item["bytes"])
    input_hashes[str(path.relative_to(DOCKET))] = digest(path)
for filename, expected in manifest["accepted_inputs"].items():
    path = DOCKET / filename
    check("hash:accepted:" + filename, digest(path) == expected)
    input_hashes[filename] = digest(path)
input_hashes[str((LAB / "MANIFEST.json").relative_to(DOCKET))] = digest(LAB / "MANIFEST.json")

results = read(LAB / "MATCHED_CONTROLS_RESULTS.json")
frozen = read(LAB / "FROZEN_MATCHING_RECEIPT.json")
rank = read(DOCKET / "rank_metrics_addendum.json")
pool_blob = read(DOCKET / "rank_metrics_pool_input.json")
pool = matrix(pool_blob)
# This matrix is an extraction of CSV cells: blank numeric cells are empty
# strings. Parse explicitly so an absent feature cannot enter common support.
for row in pool:
    for field in ("prophet_score", "intel_score", "ret_3m", "quality_z", "adv_yi", "excess_cc"):
        raw = row[field]
        row[field] = None if raw is None or raw == "" else float(raw)
        if row[field] is not None and not isfinite(row[field]):
            row[field] = None
    row["sector"] = row["sector"] or None
pool_by_key = {(row["date"], row["ticker"]): row for row in pool}
calendar = read(LAB / "benchmark_sessions_input.json")["sessions"]
calendar_index = {date: i for i, date in enumerate(calendar)}
check("source_pin", all(x["source_sha"] == SOURCE for x in (manifest, results, frozen, pool_blob)))
check("unique_pool_row_keys", len(pool_by_key) == len(pool) == 1488)
frozen_by_id = {case["case_id"]: case for case in frozen["cases"]}
graded_by_id = {case["case_id"]: case for case in results["matching_case_results"]}


def source_neighbors(case):
    candidates = [row for row in pool if row["date"] == case["date"]]
    if case["scope"] == "accepted_common_features":
        candidates = [row for row in candidates
                      if all(row[name] is not None for name in
                             ("prophet_score", "intel_score", "ret_3m", "quality_z"))]
    selected = set(case["selected_order"])
    candidate_map = {r["ticker"]: r for r in candidates if r["ticker"] not in selected}
    check("alternatives:" + case["case_id"],
          set(candidate_map) == {r["ticker"] for r in case["alternatives"]})
    output = []
    for slot in case["slots"]:
        original = pool_by_key[(case["date"], slot["ticker"])]
        matches = []
        for ticker, candidate in sorted(candidate_map.items()):
            eligible = original["sector"] is not None and candidate["sector"] == original["sector"]
            if case["specification"] == "sector_adv_0.5_to_2":
                left, right = original["adv_yi"], candidate["adv_yi"]
                eligible = eligible and left is not None and right is not None
                eligible = eligible and isfinite(left) and isfinite(right) and left > 0 and right > 0
                eligible = eligible and 0.5 <= right / left <= 2.0
            if eligible:
                matches.append(ticker)
        output.append(matches)
    check("source_neighbor_counts:" + case["case_id"],
          list(map(len, output)) == case["slot_neighbor_counts"])
    for i, neighbors in enumerate(output):
        recorded = {a["ticker"] for a in case["alternatives"] if a["slot_mask"] & (1 << i)}
        check("source_edges:" + case["case_id"] + ":" + str(i), set(neighbors) == recorded)
    return output


# A counterexample that makes the distinction observable, not just verbal.
toy_neighbors = [["x", "y"], ["x", "y", "z"]]
toy_assignments = assignments(toy_neighbors)
toy_portfolios = Counter(tuple(sorted(a)) for a in toy_assignments)
toy_values = {"x": 0.0, "y": 0.0, "z": 10.0}
assignment_mean = fmean(fmean(toy_values[t] for t in a) for a in toy_assignments)
portfolio_mean = fmean(fmean(toy_values[t] for t in a) for a in toy_portfolios)
check("toy:four_assignments_three_portfolios", len(toy_assignments) == 4 and len(toy_portfolios) == 3)
near("toy:uniform_assignment_mean", assignment_mean, 2.5)
near("toy:uniform_portfolio_mean", portfolio_mean, 10 / 3)
toy_unknown_share = Fraction(sum("z" in a for a in toy_assignments), len(toy_assignments) * 2)
check("toy:missing_probability_is_not_slot_share", toy_unknown_share == Fraction(1, 4))
# Two disjoint sectors provide a literal product-space proof of factorization.
sector_a = assignments(toy_neighbors)
sector_b = assignments([["q", "r"], ["q", "r"]])
sector_join = assignments(toy_neighbors + [["q", "r"], ["q", "r"]])
check("toy:sector_product_bijection", set(sector_join) == {a + b for a, b in product(sector_a, sector_b)})


def direct_case(case_id):
    case = frozen_by_id[case_id]
    graded = graded_by_id[case_id]
    graph_result = results["graph_outcome_results"][graded["graph_key"]]
    neighbors = source_neighbors(case)
    all_assignments = assignments(neighbors)
    k, total = len(neighbors), len(all_assignments)
    check("cartesian_assignment_count:" + case_id, total == case["full_assignment_count"])
    sectors = defaultdict(list)
    for i, slot in enumerate(case["slots"]):
        sectors[slot["sector"]].append(i)
    component_counts = {sector: len(assignments([neighbors[i] for i in indexes]))
                        for sector, indexes in sectors.items()}
    check("direct_sector_factorization:" + case_id, prod(component_counts.values()) == total)
    inclusions = Counter(t for a in all_assignments for t in a)
    complete = [a for a in all_assignments if all(observed(pool_by_key[(case["date"], t)]) for t in a)]
    check("all_observed_assignment_count:" + case_id,
          len(complete) == graph_result["all_observed_assignment_count"])
    near("all_observed_assignment_probability:" + case_id,
         len(complete) / total, graph_result["probability_all_six_control_labels_observed"])
    for row in graph_result["name_inclusions"]:
        ticker = row["ticker"]
        check("direct_inclusion:" + case_id + ":" + ticker,
              inclusions[ticker] == row["assignment_inclusion_count"])
        check("direct_slot_inclusion:" + case_id + ":" + ticker,
              [sum(a[i] == ticker for a in all_assignments) for i in range(k)]
              == row["per_slot_assignment_counts"])
    unknown = {t: n for t, n in inclusions.items() if not observed(pool_by_key[(case["date"], t)])}
    unknown_share = Fraction(sum(unknown.values()), total * k)
    near("direct_unknown_name_share:" + case_id,
         float(unknown_share), graph_result["expected_unknown_name_share"])
    known_return = fsum(n * pool_by_key[(case["date"], t)]["excess_cc"]
                       for t, n in inclusions.items() if t not in unknown) / (total * k)
    known_hits = Fraction(sum(n for t, n in inclusions.items()
                             if t not in unknown and pool_by_key[(case["date"], t)]["excess_cc"] > 0),
                          total * k)
    near("direct_known_return_contribution:" + case_id,
         known_return, graph_result["observed_return_contribution_pp"])
    precision_bounds = [float(known_hits), float(known_hits + unknown_share)]
    for i in range(2):
        near("direct_precision_bound:" + case_id + ":" + str(i),
             precision_bounds[i], graph_result["control_precision_bounds"][i])
    complete_means = [fmean(pool_by_key[(case["date"], t)]["excess_cc"] for t in a) for a in complete]
    selected_mean = fmean(pool_by_key[(case["date"], t)]["excess_cc"] for t in case["selected_order"])
    near("direct_selected_mean:" + case_id, selected_mean, graded["selected_mean_excess_pp"])
    scenarios = []
    if unknown:
        check("unknown_full_policy_mean_remains_null:" + case_id,
              graded["return_difference_pp"] is None and graph_result["exact_expected_control_excess_pp"] is None)
        for missing_value in [-20, 0, 20]:
            control_mean = known_return + float(unknown_share) * missing_value
            difference = selected_mean - control_mean
            near("direct_scenario:" + case_id + ":" + str(missing_value),
                 control_mean, graph_result["return_scenarios_unknown_excess_pp"][str(missing_value)])
            for stored in graded["missing_return_scenarios"]:
                if stored["assumed_control_unknown_excess_pp"] == missing_value:
                    near("direct_scenario_difference:" + case_id + ":" + str(missing_value),
                         difference, stored["selected_minus_control_pp"])
            scenarios.append({"unknown_excess_pp": missing_value, "expected_control_pp": control_mean,
                              "selected_minus_control_pp": difference})
    else:
        near("direct_complete_control_mean:" + case_id, fmean(complete_means),
             graph_result["exact_expected_control_excess_pp"])
        # Population variance of a uniform finite policy, not sample variance.
        near("direct_policy_population_sd:" + case_id, pstdev(complete_means),
             graph_result["exact_control_randomization_sd_pp"])
    return {"case_id": case_id, "slot_order": [s["ticker"] for s in case["slots"]],
            "neighbors_from_original_features": neighbors,
            "cartesian_tuple_n_before_distinctness": prod(map(len, neighbors)),
            "full_assignment_n": total, "unique_unordered_portfolio_n": len({tuple(sorted(a)) for a in all_assignments}),
            "sector_component_counts": component_counts, "all_observed_assignment_n": len(complete),
            "all_observed_assignment_probability": len(complete) / total,
            "unknown_inclusion_counts": unknown, "unknown_name_share_exact": str(unknown_share),
            "unknown_name_share": float(unknown_share), "known_control_return_contribution_pp": known_return,
            "control_precision_bounds_fraction": precision_bounds,
            "selected_mean_pp": selected_mean,
            "full_policy_mean_pp": known_return if not unknown else None,
            "conditional_on_observed_mean_pp": fmean(complete_means),
            "conditional_on_observed_population_variance_pp_squared": pstdev(complete_means) ** 2,
            "missing_scenarios": scenarios}


direct = [direct_case("accepted_common_features/intel_top6/sector_adv_0.5_to_2/2026-09-01"),
          direct_case("broad_qualified/featured_top6/sector_adv_0.5_to_2/2026-09-03")]

# Independently reconstruct reported aggregate effects from fixed input labels
# and frozen exact inclusion counts; the count algorithms are not reused.
aggregate_checks = []
for aggregate in results["matching_aggregates"]:
    cases = [c for c in results["matching_case_results"]
             if all(c[key] == aggregate[key] for key in ("scope", "arm", "specification"))]
    complete_cases = [c for c in cases if c["status"] == "complete_matched_comparison"]
    selected_daily, control_daily, difference_daily, precision_daily = [], [], [], []
    for case in complete_cases:
        inclusions = results["graph_outcome_results"][case["graph_key"]]["name_inclusions"]
        total, k = case["full_assignment_count"], len(case["selected_tickers"])
        check("sum_inclusion_mass:" + case["case_id"],
              sum(x["assignment_inclusion_count"] for x in inclusions) == k * total)
        source_selected = [pool_by_key[(case["date"], t)] for t in case["selected_tickers"]]
        selected = fmean(r["excess_cc"] for r in source_selected)
        control = fsum(x["assignment_inclusion_count"] * pool_by_key[(case["date"], x["ticker"])]["excess_cc"]
                       for x in inclusions) / (k * total)
        precision = fmean(r["excess_cc"] > 0 for r in source_selected) - fsum(
            x["assignment_inclusion_count"] * (pool_by_key[(case["date"], x["ticker"])]["excess_cc"] > 0)
            for x in inclusions) / (k * total)
        near("date_return_difference:" + case["case_id"], selected - control, case["return_difference_pp"])
        selected_daily.append(selected)
        control_daily.append(control)
        difference_daily.append(selected - control)
        precision_daily.append(precision)
    check("complete_dates:" + "/".join(aggregate[k] for k in ("scope", "arm", "specification")),
          len(complete_cases) == aggregate["complete_date_n"])
    if complete_cases:
        for key, values in [("mean_selected_excess_pp", selected_daily),
                            ("mean_expected_control_excess_pp", control_daily),
                            ("mean_selected_minus_expected_control_pp", difference_daily),
                            ("mean_precision_difference", precision_daily)]:
            near("aggregate:" + aggregate["arm"] + ":" + aggregate["specification"] + ":" + key,
                 fmean(values), aggregate[key])
    aggregate_checks.append({key: aggregate[key] for key in (
        "scope", "arm", "specification", "matured_pool_date_n", "complete_date_n",
        "mean_selected_excess_pp", "mean_expected_control_excess_pp", "mean_selected_minus_expected_control_pp")})

support = []
for comparison in results["common_support_comparisons"]:
    groups = [a for a in results["matching_aggregates"] if a["scope"] == comparison["scope"]
              and a["specification"] == comparison["specification"]]
    intersection = sorted(set.intersection(*(set(a["complete_comparison_dates"]) for a in groups)))
    check("common_support:" + comparison["specification"],
          intersection == comparison["all_six_arm_complete_common_dates"])
    support.append({"specification": comparison["specification"], "all_six_arm_common_dates": intersection})

primary = next(a for a in results["matching_aggregates"] if a["scope"] == "broad_qualified"
               and a["arm"] == "featured_top6" and a["specification"] == "sector_adv_0.5_to_2")
primary_cases = [c for c in results["matching_case_results"] if c["scope"] == "broad_qualified"
                 and c["arm"] == "featured_top6" and c["specification"] == "sector_adv_0.5_to_2"
                 and c["matured_pool_has_observations"]]
infeasible = [c for c in primary_cases if c["full_assignment_count"] == 0]
check("primary_support_denominators", len(primary_cases) == 17 and len(infeasible) == 8
      and primary["complete_date_n"] == 9)
envelope = [fmean(c["precision_difference_bounds"][i] for c in primary_cases) for i in (0, 1)]
for i in (0, 1):
    near("primary_hypothetical_completion_envelope:" + str(i), envelope[i],
         primary["matured_original_dates_precision_difference_bounds"][i])
hall_neighbors = [["a"], ["a"], ["b"]]
check("infeasible_is_not_unobserved_label", all(hall_neighbors) and not assignments(hall_neighbors))

# Independent date/issuer dependence counts from the original H10 row matrix.
episodes = [r for r in matrix(read(DOCKET / "v4_review_rows.json")["episode_rows"])
            if r["horizon"] == 10 and observed(r)]
episode_result = results["episode_dependence"]
by_date, by_ticker = defaultdict(list), defaultdict(list)
for row in episodes:
    by_date[row["date"]].append(row)
    by_ticker[row["ticker"]].append(row)
    check("episode_exact_H10:" + row["date"] + ":" + row["ticker"],
          calendar_index[row["exit_date"]] - calendar_index[row["entry_date"]] == 10)
dates = sorted(by_date)
check("episode_denominators", len(episodes) == 288 and len(dates) == 21 and len(by_ticker) == 249)
near("episode_row_mean", fmean(r["excess_cc"] for r in episodes), episode_result["row_weighted_mean_pp"])
near("episode_date_mean", fmean(fmean(r["excess_cc"] for r in by_date[d]) for d in dates),
     episode_result["date_weighted_mean_pp"])
windows = {}
for date, rows in by_date.items():
    endpoints = {(calendar_index[r["entry_date"]], calendar_index[r["exit_date"]]) for r in rows}
    check("one_window_per_date:" + date, len(endpoints) == 1)
    windows[date] = next(iter(endpoints))


def overlaps(left, right):
    return min(left[1], right[1]) > max(left[0], right[0])


date_overlap_n = sum(overlaps(windows[a], windows[b]) for a, b in combinations(dates, 2))
issuer_overlap_n = sum(overlaps(windows[a["date"]], windows[b["date"]])
                       for rows in by_ticker.values() for a, b in combinations(rows, 2))
check("date_overlap_count", date_overlap_n == episode_result["window_dependence"]["overlapping_date_pair_n"] == 135)
check("issuer_overlap_count", issuer_overlap_n == episode_result["window_dependence"]["repeated_issuer_overlapping_pair_n"] == 36)
independent_triples = [group for group in combinations(dates, 3)
                       if all(not overlaps(windows[a], windows[b]) for a, b in combinations(group, 2))]
independent_quads = [group for group in combinations(dates, 4)
                     if all(not overlaps(windows[a], windows[b]) for a, b in combinations(group, 2))]
check("maximum_three_nonoverlapping_windows_by_exhaustive_subsets",
      bool(independent_triples) and not independent_quads
      and episode_result["window_dependence"]["maximum_nonoverlapping_date_window_n"] == 3)
phases = []
start = min(w[0] for w in windows.values())
for phase in range(10):
    phase_dates = sorted(d for d in dates if (windows[d][0] - start) % 10 == phase)
    rows = [r for d in phase_dates for r in by_date[d]]
    original = episode_result["all_ten_nonoverlapping_phases"][phase]
    check("phase_dates:" + str(phase), phase_dates == original["dates"])
    check("phase_no_shared_return_segments:" + str(phase),
          all(not overlaps(windows[a], windows[b]) for a, b in combinations(phase_dates, 2)))
    near("phase_mean:" + str(phase), fmean(r["excess_cc"] for r in rows), original["mean_excess_pp"])
    phases.append({"phase": phase, "date_n": len(phase_dates), "row_n": len(rows),
                   "mean_excess_pp": fmean(r["excess_cc"] for r in rows)})
for group_key, rows in [("leave_one_date_out", by_date), ("leave_one_issuer_out", by_ticker)]:
    key = "date" if group_key == "leave_one_date_out" else "ticker"
    for stored in episode_result[group_key]:
        remaining = [r for r in episodes if r[key] != stored[key]]
        near(group_key + ":" + stored[key], fmean(r["excess_cc"] for r in remaining), stored["mean_without_pp"])

# One actual calendar-gap bootstrap reconstructed with a direct list of session
# indexes. RNG seed is part of the frozen experimental contract, not a new seed.
reversal = next(a for a in results["matching_aggregates"] if a["scope"] == "accepted_common_features"
                and a["arm"] == "reversal_top6" and a["specification"] == "sector_only_sensitivity")
sensitivity = reversal["date_dependence_sensitivity"]
daily_map = {r["date"]: r["mean"] for r in sensitivity["daily"]}
first, last = min(calendar_index[d] for d in daily_map), max(calendar_index[d] for d in daily_map)
span = calendar[first:last + 1]
block = sensitivity["calendar_block_5"]
rng = np.random.default_rng(block["seed"])
starts = rng.integers(0, len(span), size=(10000, ceil(len(span) / 5)))
draws, empty_n = [], 0
for start_row in starts:
    sampled_dates = [span[(int(s) + j) % len(span)] for s in start_row for j in range(5)][:len(span)]
    sample_values = [daily_map[d] for d in sampled_dates if d in daily_map]
    if sample_values:
        draws.append(fmean(sample_values))
    else:
        empty_n += 1
check("calendar_gap_draw_counts", empty_n == block["invalid_n"] == 168 and len(draws) == 9832)
independent_percentiles = list(map(float, np.percentile(draws, [2.5, 97.5])))
for i in (0, 1):
    near("calendar_gap_conditional_percentile:" + str(i), independent_percentiles[i], block["percentile_95"][i])

# Rebuild all paired observations from original outcome labels and recorded
# original memberships. No analysis implementation or stored SD is imported.
paired_by_arm = defaultdict(list)
daily_by_date = {row["date"]: row for row in rank["accepted_daily_reconstruction"]}
intended_by_date = {row["date"]: row for row in rank["intended_intel_tiebreak_top6"]["daily"]}
for date in rank["common_dates"]:
    daily = daily_by_date[date]
    score = fmean(pool_by_key[(date, t)]["excess_cc"] for t in daily["arms"]["score_top6"]["tickers"])
    for arm in ("intel_top6", "momentum_top6", "reversal_top6", "quality_top6", "intended_intel_top6"):
        names = intended_by_date[date]["new_tickers"] if arm == "intended_intel_top6" else daily["arms"][arm]["tickers"]
        value = fmean(pool_by_key[(date, t)]["excess_cc"] for t in names)
        paired_by_arm[arm].append(value - score)
power_checks = []
z_lower = 1.959963984540054
power_quantile = {0.8: 0.8416212335729143, 0.9: 1.2815515655446004}
grid_n = 0
for arm_result in results["power_planning"]["arms"]:
    values = paired_by_arm[arm_result["arm"]]
    sd = stdev(values)
    near("paired_mean:" + arm_result["arm"], fmean(values), arm_result["observed_mean_difference_pp"])
    near("paired_sample_sd:" + arm_result["arm"], sd, arm_result["observed_paired_daily_sd_pp"])
    base_requirements = {}
    for row in arm_result["grid"]:
        margin = row["true_effect_pp"] - 0.25
        n = ceil(((z_lower + power_quantile[row["power"]]) * sd * row["sd_multiplier"] / margin) ** 2)
        check("power_grid:" + arm_result["arm"] + ":" + str(grid_n), n == row["independent_date_equivalents"])
        for multiplier, reported in row["illustrative_observed_date_requirements_by_dependence_multiplier"].items():
            check("power_multiplier:" + str(grid_n) + ":" + multiplier, n * int(multiplier) == reported)
        if row["power"] == 0.8 and row["sd_multiplier"] == 1:
            base_requirements[str(row["true_effect_pp"])] = n
        grid_n += 1
    near("detect_point_two_five_vs_zero:" + arm_result["arm"],
         base_requirements["0.5"], arm_result["detect_0.25_pp_vs_zero_at_80pct_iid_date_equivalents"])
    power_checks.append({"arm": arm_result["arm"], "paired_date_n": len(values), "paired_mean_pp": fmean(values),
                         "paired_sample_sd_pp": sd, "80pct_power_baseline_sd_independent_date_equivalents": base_requirements})

# Confirm every original file remains byte-for-byte unchanged after this review.
for relative, expected in input_hashes.items():
    check("after_review_hash:" + relative, digest(DOCKET / relative) == expected)

output = {
    "schema": "cn_prophet_matched_controls_independent_review_v1",
    "source_sha": SOURCE,
    "status": "ACCEPTED_WITH_ONE_INTERPRETATION_QUALIFICATION",
    "review_script_sha256": digest(Path(__file__)),
    "input_sha256": input_hashes,
    "independence": {"author_role": "independent reviewing subagent", "producer_code_imported_or_executed": False,
                     "direct_oracle": "Cartesian product of rebuilt source-feature neighbors, filtered by distinct names",
                     "scope": "Two real graph enumerations plus a synthetic distribution/factorization falsifier; source-label aggregation, dependence and power independently rebuilt. This is not a second enumeration of all 109344 producer-oracle assignments."},
    "toy_assignment_policy": {"neighbors": toy_neighbors, "assignments": toy_assignments,
                              "portfolio_multiplicities": [{"portfolio": list(p), "assignment_n": n} for p, n in toy_portfolios.items()],
                              "uniform_assignment_mean_pp": assignment_mean, "uniform_unique_portfolio_mean_pp": portfolio_mean,
                              "missing_z_assignment_probability": 0.5, "missing_z_name_share": float(toy_unknown_share),
                              "disjoint_sector_component_counts": [len(sector_a), len(sector_b)], "combined_count": len(sector_join)},
    "direct_real_graphs": direct,
    "aggregate_reconstructions": aggregate_checks,
    "common_support": support,
    "strict_policy_support_qualification": {
        "original_matured_dates": len(primary_cases), "feasible_complete_dates": 9,
        "infeasible_dates": [c["date"] for c in infeasible],
        "strict_full_cohort_estimand": None,
        "strict_full_cohort_status": "UNAVAILABLE_NO_FULL_ASSIGNMENT_ON_EIGHT_DATES",
        "reported_conservative_completion_envelope_fraction": envelope,
        "reported_conservative_completion_envelope_percentage_points": [100 * x for x in envelope],
        "meaning": "An envelope over arbitrary hypothetical completions on unsupported dates. A uniform draw from an empty assignment set does not exist. Do not export this envelope as an identified bound for the strict full-cohort policy.",
        "hall_fixture": {"neighbors": hall_neighbors, "all_slots_nonempty": True, "full_assignments": assignments(hall_neighbors)}},
    "episode_dependence_reconstruction": {
        "episode_n": len(episodes), "date_n": len(dates), "issuer_n": len(by_ticker),
        "repeat_observation_n": len(episodes) - len(by_ticker),
        "repeated_issuer_n": sum(len(v) > 1 for v in by_ticker.values()),
        "row_mean_excess_pp": fmean(r["excess_cc"] for r in episodes),
        "date_pairs": len(list(combinations(dates, 2))), "overlapping_date_pairs": date_overlap_n,
        "same_issuer_overlapping_pairs": issuer_overlap_n,
        "nonoverlapping_triples_found": len(independent_triples), "nonoverlapping_quadruples_found": len(independent_quads),
        "max_nonoverlapping_windows": 3, "all_ten_phases": phases,
        "interpretation": "Structural counts and descriptive resampling; neither maximum nonoverlap nor multiplicity bootstrap estimates a certified effective sample size."},
    "calendar_gap_bootstrap_reconstruction": {"case": "accepted_common_features/reversal_top6/sector_only_sensitivity",
                                             "calendar_sessions": len(span), "observed_dates": len(daily_map),
                                             "block_sessions": 5, "replicates": 10000, "empty_replicates": empty_n,
                                             "finite_replicates": len(draws), "finite_only_percentile_95_pp": independent_percentiles,
                                             "interpretation": "Conditional descriptive sensitivity on nonempty resamples; no calibrated confidence claim."},
    "power_reconstruction": {"grid_rows_checked": grid_n, "z_lower": z_lower, "z_power": power_quantile,
                             "units": "percentage points of paired daily H10 excess difference; independent date equivalents",
                             "formula": "ceil(((z_0.975 + z_power) * sample_SD * SD_multiplier / (true_effect_pp - 0.25)) ** 2)",
                             "arms": power_checks,
                             "interpretation": "Known-variance normal approximation using an unstable eleven-date sample SD as a planning scenario; not a release schedule, calibrated power guarantee, or prospective trading date target."},
    "verification": {"check_count": len(CHECKS), "pass_count": sum(c["status"] == "PASS" for c in CHECKS),
                     "fail_count": sum(c["status"] == "FAIL" for c in CHECKS), "original_input_hashes_unchanged": True,
                     "numpy_version": np.__version__, "python_version": sys.version},
    "checks": CHECKS,
}
(OUT / "REVIEW_EVIDENCE.json").write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n")
print(json.dumps({"status": output["status"], "checks": len(CHECKS), "direct_assignments_enumerated": sum(x["full_assignment_n"] for x in direct),
                  "power_grid_rows_checked": grid_n, "output_sha256": digest(OUT / "REVIEW_EVIDENCE.json")}, sort_keys=True))
