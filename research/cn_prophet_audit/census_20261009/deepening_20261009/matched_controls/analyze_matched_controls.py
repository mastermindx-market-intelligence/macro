#!/usr/bin/env python3
"""Exact matched controls and dependence sensitivity on immutable audit outputs.

No network, price grading, repository import or production mutation. The frozen
graph receipt is written before any new matching-outcome statistic is computed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
from statistics import NormalDist, fmean, stdev

import numpy as np


SOURCE_SHA = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"
DESIGN_SHA = "d8a40683dd0727d72df7d520a98ee587cf07ea28045901bbc109e0845b2052ef"
INPUT_HASHES = {
    "rank_metrics_pool_input.json": "1f6708ca0e8ec12d2983900f5d5d0313a9272e726730d7a91a220b4165bb6976",
    "rank_metrics_addendum.json": "d514efe4c8bcb624603d32ab6c0ece6b3ef2292c858f83ebc1e55e8834985dbc",
    "v4_review_rows.json": "626aacda09bdef9ba6cd8bb01a3688e445228b48ce63d5496defb07ce0482830",
    "historical_evidence.json": "8b651cf4df19736f66a3cf184c5a47478ffe0bf2fc62a24bb5452c01b836e54d",
}
CALENDAR_SHA = "6be35e860db377f8a1a154c65cf55de2581e2ff222191582219e2c286091f30e"
REPLICATES = 10000
BASE_SEED = 2026100934
K = 6
FEATURES = ["prophet_score", "intel_score", "ret_3m", "quality_z"]
ARMS = {
    "score_top6": [("prophet_score", -1)],
    "intel_top6": [("intel_score", -1)],
    "momentum_top6": [("ret_3m", -1)],
    "reversal_top6": [("ret_3m", 1)],
    "quality_top6": [("quality_z", -1)],
    "intended_intel_top6": [("intel_score", -1), ("prophet_score", -1)],
}


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def near(a, b, message, tol=1e-9):
    check(math.isclose(a, b, rel_tol=tol, abs_tol=tol), message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stable_seed(label):
    return BASE_SEED + int(sha(label.encode())[:12], 16)


def records(matrix):
    columns = matrix["columns"]
    check(len(columns) == len(set(columns)), "Duplicate matrix column")
    return [dict(zip(columns, values, strict=True)) for values in matrix["data"]]


def number(value):
    if value is None or value == "":
        return None
    value = float(value)
    check(math.isfinite(value), "Nonfinite numeric input")
    return value


def load_inputs(docket, output):
    check(sha((output / "DESIGN.md").read_bytes()) == DESIGN_SHA, "Design changed after freeze")
    result = {}
    for name, expected in INPUT_HASHES.items():
        data = (docket / name).read_bytes()
        check(sha(data) == expected, "Unaccepted input: " + name)
        result[name] = json.loads(data)
    data = (output / "benchmark_sessions_input.json").read_bytes()
    check(sha(data) == CALENDAR_SHA, "Calendar extraction changed")
    calendar = json.loads(data)
    evidence = result["historical_evidence.json"]["autopsy"]
    check(calendar["source_sha"] == evidence["source_sha"] == SOURCE_SHA, "Study pin mismatch")
    benchmark = evidence["blobs"][calendar["source_path"]]
    check(benchmark["sha256"] == calendar["source_sha256"], "Benchmark input blob differs")
    check(benchmark["bytes"] == calendar["source_bytes"], "Benchmark size differs")
    check(calendar["sessions"] == sorted(set(calendar["sessions"])), "Calendar is not ordered unique")
    return result, calendar


def parse_pool(matrix):
    result = records(matrix)
    numeric = FEATURES + ["adv_yi", "lane_rank", "score_rank", "pnl_cc", "benchmark_cc", "excess_cc"]
    for row in result:
        for field in numeric:
            row[field] = number(row[field])
        row["sector"] = row["sector"] or None
        check(row["board_definition"] == "cn_prophet_v4" and row["horizon"] == "10", "Unexpected pool slice")
        check(row["lane"] == "featured" or (row["lane"] == "more_actionable" and row["lane_reasons"] in ["featured_cap", "sector_cap"]), "Unqualified input row")
        if row["status"] == "observed":
            check(row["excess_cc"] is not None, "Observed row lacks return")
            near(row["pnl_cc"] - row["benchmark_cc"], row["excess_cc"], "Return identity differs")
    check(len(result) == 1488, "Qualified denominator changed")
    check(len({(r["date"], r["ticker"]) for r in result}) == len(result), "Duplicate pool key")
    return result


def select(rows, keys):
    # This function accesses only decision fields; never status or outcomes.
    ordered = sorted((r for r in rows if all(r[field] is not None for field, _ in keys)),
                     key=lambda r: tuple(direction * r[field] for field, direction in keys) + (r["ticker"],))
    chosen, counts = [], Counter()
    for row in ordered:
        if counts[row["sector"]] >= 4:
            continue
        chosen.append(row)
        counts[row["sector"]] += 1
        if len(chosen) == K:
            break
    return chosen


def count_table(allowed, k):
    """suffix[i][mask]: injections of exactly mask slots using candidates i..N."""
    size = 1 << k
    suffix = [[0] * size for _ in range(len(allowed) + 1)]
    suffix[-1][0] = 1
    for i in range(len(allowed) - 1, -1, -1):
        nxt, cur = suffix[i + 1], suffix[i]
        for mask in range(size):
            value, bits = nxt[mask], mask & allowed[i]
            while bits:
                bit = bits & -bits
                bits -= bit
                value += nxt[mask ^ bit]
            cur[mask] = value
    return suffix


def exact_inclusions(allowed, k, suffix):
    size, full = 1 << k, (1 << k) - 1
    prefix = [0] * size
    prefix[0] = 1
    incidence = []
    for i, edges in enumerate(allowed):
        counts = [0] * k
        for mask, ways in enumerate(prefix):
            if not ways:
                continue
            bits = edges & (full ^ mask)
            while bits:
                bit = bits & -bits
                bits -= bit
                slot = bit.bit_length() - 1
                counts[slot] += ways * suffix[i + 1][full ^ (mask | bit)]
        incidence.append(counts)
        nxt = prefix.copy()
        for mask, ways in enumerate(prefix):
            if not ways:
                continue
            bits = edges & (full ^ mask)
            while bits:
                bit = bits & -bits
                bits -= bit
                nxt[mask | bit] += ways
        prefix = nxt
    total = suffix[0][full]
    if total:
        for slot in range(k):
            check(sum(row[slot] for row in incidence) == total, "Slot marginal does not sum to one")
        check(sum(map(sum, incidence)) == k * total, "Wrong total inclusion weight")
        check(all(sum(row) <= total for row in incidence), "Name used more than once")
    return incidence


def exact_total_moments(allowed, values, k):
    """Count and first/second moments of selected total, without enumerating."""
    size, full = 1 << k, (1 << k) - 1
    count, sums, squares = [0] * size, [0.0] * size, [0.0] * size
    count[0] = 1
    for edges, value in zip(allowed, values, strict=True):
        nc, ns, nq = count.copy(), sums.copy(), squares.copy()
        for mask, ways in enumerate(count):
            if not ways:
                continue
            bits = edges & (full ^ mask)
            while bits:
                bit = bits & -bits
                bits -= bit
                target = mask | bit
                nc[target] += ways
                ns[target] += sums[mask] + value * ways
                nq[target] += squares[mask] + 2 * value * sums[mask] + value * value * ways
        count, sums, squares = nc, ns, nq
    return count[full], sums[full], squares[full]


def sample_assignment(allowed, k, suffix, rng):
    remaining, result = (1 << k) - 1, [-1] * k
    check(suffix[0][remaining] > 0, "Cannot sample infeasible graph")
    for i, edges in enumerate(allowed):
        if not remaining:
            break
        draw = rng.randrange(suffix[i][remaining])
        skipped = suffix[i + 1][remaining]
        if draw < skipped:
            continue
        draw -= skipped
        bits = remaining & edges
        while bits:
            bit = bits & -bits
            bits -= bit
            ways = suffix[i + 1][remaining ^ bit]
            if draw < ways:
                result[bit.bit_length() - 1] = i
                remaining ^= bit
                break
            draw -= ways
        else:
            raise AssertionError("Conditional sampler exhausted valid choices")
    check(remaining == 0 and len(set(result)) == k and min(result) >= 0, "Incomplete sampled matching")
    return result


def graph_signature(slots, alternatives, specification):
    def fields(row):
        return [row["ticker"], row["sector"], row["adv_yi"]]
    payload = [specification, [fields(r) for r in slots], [fields(r) for r in alternatives]]
    return sha(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())


def build_graph(selected, pool, specification):
    slots = sorted(selected, key=lambda r: r["ticker"])
    original = {r["ticker"] for r in slots}
    alternatives = sorted((r for r in pool if r["ticker"] not in original), key=lambda r: r["ticker"])
    allowed = []
    for candidate in alternatives:
        mask = 0
        for s, slot in enumerate(slots):
            sector_ok = slot["sector"] is not None and candidate["sector"] == slot["sector"]
            adv_ok = all(r["adv_yi"] is not None and r["adv_yi"] > 0 for r in [slot, candidate])
            if specification == "sector_adv_0.5_to_2":
                adv_ok = adv_ok and slot["adv_yi"] * .5 <= candidate["adv_yi"] <= slot["adv_yi"] * 2
            else:
                check(specification == "sector_only_sensitivity", "Unexpected matching specification")
                adv_ok = True
            if sector_ok and adv_ok:
                mask |= 1 << s
        allowed.append(mask)
    suffix = count_table(allowed, K)
    full = (1 << K) - 1
    maximum = max(mask.bit_count() for mask, ways in enumerate(suffix[0]) if ways)
    witnesses = []
    for mask in range(1, full + 1):
        neighbors = sum(bool(edges & mask) for edges in allowed)
        deficiency = mask.bit_count() - neighbors
        if deficiency > 0:
            witnesses.append({"slots": [slots[i]["ticker"] for i in range(K) if mask & (1 << i)],
                              "distinct_neighbor_n": neighbors, "deficiency": deficiency})
    witnesses.sort(key=lambda row: (-row["deficiency"], len(row["slots"]), row["slots"]))
    check(bool(suffix[0][full]) == (not witnesses), "Hall feasibility contradiction")
    return {"slots": slots, "alternatives": alternatives, "allowed": allowed, "suffix": suffix,
            "total": suffix[0][full], "maximum": maximum, "hall_witness": witnesses[0] if witnesses else None,
            "signature": graph_signature(slots, alternatives, specification)}


def frozen_receipt(case, graph):
    return {"case_id": case["case_id"], "date": case["date"], "scope": case["scope"], "arm": case["arm"],
            "specification": case["specification"], "selected_order": [r["ticker"] for r in case["selected"]],
            "slots": [{key: r[key] for key in ["ticker", "sector", "adv_yi"]} for r in graph["slots"]],
            "alternatives": [{"ticker": r["ticker"], "sector": r["sector"], "adv_yi": r["adv_yi"],
                              "slot_mask": mask} for r, mask in zip(graph["alternatives"], graph["allowed"], strict=True)],
            "slot_neighbor_counts": [sum(bool(mask & (1 << s)) for mask in graph["allowed"]) for s in range(K)],
            "maximum_distinct_matching_size": graph["maximum"], "full_assignment_count": graph["total"],
            "hall_witness": graph["hall_witness"], "graph_signature": graph["signature"]}


def make_cases(pool, evidence, rank_addendum):
    groups = defaultdict(list)
    for row in pool:
        groups[row["date"]].append(row)
    discordant = sorted(r["date"] for r in evidence["cohort_vintage_coherence"]
                        if r["definition"] == "cn_prophet_v4" and (not r["same_featured_set"] or r["score_disagreements"]))
    accepted = {r["date"]: r for r in rank_addendum["accepted_daily_reconstruction"]}
    cases, gates, cache = [], [], {}
    intended = {r["date"]: r["new_tickers"] for r in rank_addendum["intended_intel_tiebreak_top6"]["daily"]}
    for date, qualified in sorted(groups.items()):
        gate = {"date": date, "qualified_n": len(qualified), "vintage_discordant": date in discordant}
        if date in discordant:
            gate["gate"] = "existing_vintage_exclusion"
            gates.append(gate)
            continue
        selections = {}
        featured = sorted((r for r in qualified if r["lane"] == "featured"), key=lambda r: (r["lane_rank"], r["ticker"]))[:K]
        selections[("broad_qualified", "featured_top6")] = (featured, qualified)
        selections[("broad_qualified", "score_top6")] = (select(qualified, ARMS["score_top6"]), qualified)
        if date in accepted:
            common = [r for r in qualified if all(r[field] is not None for field in FEATURES)]
            for arm, keys in ARMS.items():
                chosen = select(common, keys)
                expected = intended[date] if arm == "intended_intel_top6" else accepted[date]["arms"][arm]["tickers"]
                check([r["ticker"] for r in chosen] == expected, "Accepted arm membership/order changed")
                selections[("accepted_common_features", arm)] = (chosen, common)
        gate["gate"] = "frozen_pre_outcome"
        gate["selection_sizes"] = {"/".join(key): len(value[0]) for key, value in selections.items()}
        gates.append(gate)
        for (scope, arm), (selected, original_pool) in selections.items():
            if len(selected) != K:
                continue
            for specification in ["sector_adv_0.5_to_2", "sector_only_sensitivity"]:
                graph = build_graph(selected, original_pool, specification)
                key = date + ":" + graph["signature"]
                cache.setdefault(key, graph)
                cases.append({"case_id": "/".join([scope, arm, specification, date]), "date": date,
                              "scope": scope, "arm": arm, "specification": specification,
                              "selected": selected, "pool": original_pool, "graph_key": key})
    return cases, cache, gates, discordant


def distribution(values):
    values = np.asarray(values, dtype=float)
    good = values[np.isfinite(values)]
    if not len(good):
        return {"replicates": len(values), "valid_n": 0, "invalid_n": len(values), "mean": None,
                "standard_deviation": None, "percentile_95": None}
    return {"replicates": len(values), "valid_n": len(good), "invalid_n": len(values) - len(good),
            "mean": float(np.mean(good)), "standard_deviation": float(np.std(good, ddof=1)) if len(good) > 1 else None,
            "percentile_95": np.quantile(good, [.025, .975], method="linear").tolist()}


def calendar_block_weights(span, length, seed):
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, span, size=(REPLICATES, math.ceil(span / length)))
    indices = ((starts[:, :, None] + np.arange(length)) % span).reshape(REPLICATES, -1)[:, :span]
    weights = np.zeros((REPLICATES, span), dtype=np.int16)
    np.add.at(weights, (np.repeat(np.arange(REPLICATES), span), indices.ravel()), 1)
    return weights


def series_sensitivity(dates, sums, counts, sessions, label):
    check(len(dates) == len(set(dates)), "Duplicate date in sensitivity series")
    order = np.argsort(dates)
    dates = [dates[i] for i in order]
    sums, counts = np.asarray(sums, dtype=float)[order], np.asarray(counts, dtype=float)[order]
    check(np.all(counts > 0), "Observed date needs positive denominator")
    first, last = sessions.index(dates[0]), sessions.index(dates[-1])
    span = last - first + 1
    xs, ns = np.zeros(span), np.zeros(span)
    for date, total, n in zip(dates, sums, counts, strict=True):
        index = sessions.index(date) - first
        xs[index], ns[index] = total, n
    result = {"dates": dates, "n_dates": len(dates), "calendar_session_span": span,
              "calendar_no_observation_sessions": span - len(dates), "n_observations": int(sum(counts)),
              "row_weighted_mean_pp": float(sum(sums) / sum(counts)),
              "date_weighted_mean_pp": float(np.mean(sums / counts)),
              "daily": [{"date": d, "sum": float(s), "n": int(n), "mean": float(s / n)} for d, s, n in zip(dates, sums, counts, strict=True)]}
    if len(dates) < 2:
        result["uncertainty_status"] = "fewer_than_two_dates"
        return result, {}
    # Share draws across identical date cohorts, including identical arm series.
    # Arm names must not manufacture different uncertainty endpoints.
    iid_seed = stable_seed("cohort:" + "|".join(dates) + ":iid_date")
    rng = np.random.default_rng(iid_seed)
    sampled = rng.integers(0, len(dates), size=(REPLICATES, len(dates)))
    iid = sums[sampled].sum(axis=1) / counts[sampled].sum(axis=1)
    result["iid_date_reference"] = {"seed": iid_seed, **distribution(iid)}
    arrays = {"iid_date_reference": iid}
    for length in [5, 10]:
        seed = stable_seed("calendar:" + sessions[first] + ":" + sessions[last] + ":block" + str(length))
        weights = calendar_block_weights(span, length, seed)
        denominator = weights @ ns
        with np.errstate(divide="ignore", invalid="ignore"):
            sampled_means = (weights @ xs) / denominator
        key = "calendar_block_" + str(length)
        result[key] = {"seed": seed, "block_sessions": length,
                       "calendar_span_in_block_lengths": span / length,
                       "degenerate_due_to_span": span <= length,
                       "span_warning": "Whole-span circular rotation; zero-width range is not an uncertainty estimate." if span <= length else None,
                       **distribution(sampled_means)}
        iid_sd, block_sd = float(np.std(iid, ddof=1)), result[key]["standard_deviation"]
        result[key]["se_ratio_to_iid_date"] = block_sd / iid_sd if iid_sd and block_sd is not None else None
        arrays[key] = sampled_means
    result["interpretation"] = "Descriptive resampling sensitivity; few blocks, gaps, shared market regime and overlapping labels prevent a calibrated confidence guarantee."
    return result, arrays


def graph_outcomes(graph, graph_key):
    total = graph["total"]
    if not total:
        return {"full_assignment_count": 0}, None
    allowed, alternatives = graph["allowed"], graph["alternatives"]
    incidence = exact_inclusions(allowed, K, graph["suffix"])
    inclusion = [sum(row) / total for row in incidence]
    observed = [r["status"] == "observed" and r["excess_cc"] is not None for r in alternatives]
    observed_allowed = [mask if ok else 0 for mask, ok in zip(allowed, observed, strict=True)]
    observed_count = count_table(observed_allowed, K)[0][(1 << K) - 1]
    unknown_share = sum(p for p, ok in zip(inclusion, observed, strict=True) if not ok) / K
    known_return = sum(p * r["excess_cc"] for p, r, ok in zip(inclusion, alternatives, observed, strict=True) if ok) / K
    known_hits = sum(p * (r["excess_cc"] > 0) for p, r, ok in zip(inclusion, alternatives, observed, strict=True) if ok) / K
    complete = observed_count == total
    result = {"full_assignment_count": total, "all_observed_assignment_count": observed_count,
              "probability_all_six_control_labels_observed": observed_count / total,
              "policy_outcomes_complete": complete, "expected_unknown_name_share": unknown_share,
              "observed_return_contribution_pp": known_return,
              "exact_expected_control_excess_pp": known_return if complete else None,
              "control_precision_bounds": [known_hits, known_hits + unknown_share],
              "return_scenarios_unknown_excess_pp": {str(value): known_return + unknown_share * value for value in [-20, 0, 20]},
              "unrestricted_return_bounds": "No finite two-sided bound when any support label is unknown." if not complete else None,
              "name_inclusions": [{"ticker": r["ticker"], "status": r["status"], "assignment_inclusion_count": sum(counts),
                                   "inclusion_probability": p, "per_slot_assignment_counts": counts}
                                  for r, p, counts in zip(alternatives, inclusion, incidence, strict=True) if p]}
    if complete:
        ways, value_sum, value_square = exact_total_moments(allowed, [r["excess_cc"] if ok else 0.0 for r, ok in zip(alternatives, observed, strict=True)], K)
        check(ways == total, "Moment count differs")
        mean = value_sum / total / K
        near(mean, known_return, "Marginal and moment means differ")
        result["exact_control_randomization_sd_pp"] = math.sqrt(max(0.0, value_square / total / K ** 2 - mean ** 2))
    # Sampling never replaces unknown names. If no assignment can be graded,
    # the exact zero observation probability already resolves the sampling question.
    if not observed_count:
        result["sampling"] = {"status": "no_fully_observed_assignment", "replicates": 0}
        return result, np.full(REPLICATES, np.nan)
    seed = stable_seed(graph_key)
    rng = random.Random(seed)
    values = np.full(REPLICATES, np.nan)
    examples, digest = [], hashlib.sha256()
    for draw in range(REPLICATES):
        assignment = sample_assignment(allowed, K, graph["suffix"], rng)
        tickers = [alternatives[i]["ticker"] for i in assignment]
        digest.update(("|".join(tickers) + "\n").encode())
        if draw < 3:
            examples.append(tickers)
        if all(observed[i] for i in assignment):
            values[draw] = fmean(alternatives[i]["excess_cc"] for i in assignment)
    result["sampling"] = {"seed": seed, "assignment_stream_sha256": digest.hexdigest(),
                          "first_three_assignments_in_slot_order": examples,
                          "all_draws": distribution(values),
                          "interpretation": "Conditional policy variability. Any finite-only summary conditions on fully observed assignments and does not replace the unresolved full policy."}
    if complete:
        sample_se = result["exact_control_randomization_sd_pp"] / math.sqrt(REPLICATES)
        result["sampling"]["mean_error_in_mc_standard_errors"] = (float(np.mean(values)) - known_return) / sample_se if sample_se else 0.0
    return result, values


def grade_case(case, graph, outcome):
    selected = case["selected"]
    observed = [r["status"] == "observed" and r["excess_cc"] is not None for r in selected]
    unknown = sum(not ok for ok in observed)
    selected_contribution = sum(r["excess_cc"] for r, ok in zip(selected, observed, strict=True) if ok) / K
    selected_known_precision = sum(r["excess_cc"] > 0 for r, ok in zip(selected, observed, strict=True) if ok) / K
    result = {"case_id": case["case_id"], "date": case["date"], "scope": case["scope"], "arm": case["arm"],
              "specification": case["specification"], "graph_key": case["graph_key"],
              "pool_n": len(case["pool"]), "pool_status_counts": dict(Counter(r["status"] for r in case["pool"])),
              "matured_pool_has_observations": any(r["status"] == "observed" for r in case["pool"]),
              "selected_tickers": [r["ticker"] for r in selected],
              "selected_unresolved": [{"ticker": r["ticker"], "status": r["status"]} for r, ok in zip(selected, observed, strict=True) if not ok],
              "selected_mean_excess_pp": selected_contribution if not unknown else None,
              "selected_precision_bounds": [selected_known_precision, selected_known_precision + unknown / K],
              "maximum_matching_size": graph["maximum"], "full_assignment_count": graph["total"],
              "slot_neighbor_counts": [sum(bool(mask & (1 << s)) for mask in graph["allowed"]) for s in range(K)]}
    if not graph["total"]:
        result.update(status="infeasible_full_matching", precision_difference_bounds=[-1.0, 1.0], return_difference_pp=None)
        return result
    lo, hi = outcome["control_precision_bounds"]
    selected_lo, selected_hi = result["selected_precision_bounds"]
    result["precision_difference_bounds"] = [selected_lo - hi, selected_hi - lo]
    complete = not unknown and outcome["policy_outcomes_complete"]
    result["status"] = "complete_matched_comparison" if complete else "unresolved_original_or_control_policy_labels"
    result["exact_expected_control_excess_pp"] = outcome["exact_expected_control_excess_pp"]
    result["return_difference_pp"] = selected_contribution - outcome["exact_expected_control_excess_pp"] if complete else None
    result["control_unknown_name_share"] = outcome["expected_unknown_name_share"]
    result["all_six_control_labels_observed_probability"] = outcome["probability_all_six_control_labels_observed"]
    result["missing_return_scenarios"] = [{"assumed_selected_unknown_excess_pp": selected_value,
                                          "assumed_control_unknown_excess_pp": control_value,
                                          "selected_minus_control_pp": selected_contribution + unknown / K * selected_value
                                          - outcome["return_scenarios_unknown_excess_pp"][str(control_value)]}
                                         for selected_value in [-20, 0, 20] for control_value in [-20, 0, 20]] if not complete else []
    return result


def matching_aggregates(graded, graph_outputs, graph_samples, sessions):
    groups = defaultdict(list)
    for row in graded:
        groups[(row["scope"], row["arm"], row["specification"])].append(row)
    result = []
    for (scope, arm, specification), rows in sorted(groups.items()):
        rows.sort(key=lambda r: r["date"])
        mature = [r for r in rows if r["matured_pool_has_observations"]]
        complete = [r for r in rows if r["status"] == "complete_matched_comparison"]
        item = {"scope": scope, "arm": arm, "specification": specification,
                "attempted_dates": [r["date"] for r in rows], "attempted_date_n": len(rows),
                "matured_pool_dates": [r["date"] for r in mature], "matured_pool_date_n": len(mature),
                "status_counts_all_dates": dict(Counter(r["status"] for r in rows)),
                "status_counts_matured_dates": dict(Counter(r["status"] for r in mature)),
                "complete_comparison_dates": [r["date"] for r in complete], "complete_date_n": len(complete),
                "matured_slot_nonempty_n": sum(sum(n > 0 for n in r["slot_neighbor_counts"]) for r in mature),
                "matured_slot_total_n": K * len(mature),
                "matured_dates_all_slots_nonempty": sum(all(n > 0 for n in r["slot_neighbor_counts"]) for r in mature),
                "matured_dates_full_matching": sum(r["full_assignment_count"] > 0 for r in mature)}
        for label, cohort in [("all_original_dates", rows), ("matured_original_dates", mature)]:
            item[label + "_precision_difference_bounds"] = [fmean(r["precision_difference_bounds"][i] for r in cohort) for i in [0, 1]] if cohort else None
        if complete:
            differences = [r["return_difference_pp"] for r in complete]
            item["mean_selected_excess_pp"] = fmean(r["selected_mean_excess_pp"] for r in complete)
            item["mean_expected_control_excess_pp"] = fmean(r["exact_expected_control_excess_pp"] for r in complete)
            item["mean_selected_minus_expected_control_pp"] = fmean(differences)
            item["mean_precision_difference"] = fmean(r["precision_difference_bounds"][0] for r in complete)
            sensitivity, _ = series_sensitivity([r["date"] for r in complete], differences, [1] * len(complete), sessions,
                                                "matched:" + "/".join([scope, arm, specification]))
            item["date_dependence_sensitivity"] = sensitivity
            samples = np.mean([r["selected_mean_excess_pp"] - graph_samples[r["graph_key"]] for r in complete], axis=0)
            item["conditional_matching_randomization"] = {**distribution(samples),
                                                          "fraction_random_control_at_least_selected": float(np.mean(samples <= 0)),
                                                          "interpretation": "Variation from the explicitly defined random control policy on fixed realized outcomes; not an inferential p-value."}
        result.append(item)
    # Support comparison deliberately uses intersection, not arm-specific means.
    comparisons = []
    for specification in ["sector_adv_0.5_to_2", "sector_only_sensitivity"]:
        arms = list(ARMS)
        arm_rows = {arm: {r["date"]: r for r in graded if r["scope"] == "accepted_common_features" and r["specification"] == specification and r["arm"] == arm and r["status"] == "complete_matched_comparison"} for arm in arms}
        common = sorted(set.intersection(*(set(value) for value in arm_rows.values())))
        comparisons.append({"scope": "accepted_common_features", "specification": specification,
                            "all_six_arm_complete_common_dates": common, "common_date_n": len(common),
                            "arms": [{"arm": arm, "mean_selected_minus_control_pp": fmean(arm_rows[arm][d]["return_difference_pp"] for d in common) if common else None} for arm in arms]})
    featured = next(r for r in result if r["scope"] == "broad_qualified" and r["arm"] == "featured_top6" and r["specification"] == "sector_adv_0.5_to_2")
    check(featured["matured_pool_date_n"] == 17 and featured["matured_slot_nonempty_n"] == 82 and featured["matured_slot_total_n"] == 102 and featured["matured_dates_all_slots_nonempty"] == 9, "Original matchability control changed")
    return result, comparisons


def episode_dependence(review, evidence, sessions):
    all_rows = records(review["episode_rows"])
    rows = [r for r in all_rows if r["horizon"] == 10 and r["status"] == "observed"]
    check(len(rows) == 288 and len({r["date"] for r in rows}) == 21, "Accepted episode cohort changed")
    for row in rows:
        check(sessions.index(row["exit_date"]) - sessions.index(row["entry_date"]) == 10, "H10 endpoint mismatch")
    accepted = next(r for r in evidence["episode_horizons"] if r["board_definition"] == "cn_prophet_v4" and r["horizon"] == 10)
    near(fmean(r["excess_cc"] for r in rows), accepted["mean_pct"], "Accepted episode mean changed")
    by_date, by_name = defaultdict(list), defaultdict(list)
    for row in rows:
        by_date[row["date"]].append(row)
        by_name[row["ticker"]].append(row)
    dates, names = sorted(by_date), sorted(by_name)
    totals = [sum(r["excess_cc"] for r in by_date[d]) for d in dates]
    counts = [len(by_date[d]) for d in dates]
    result, _ = series_sensitivity(dates, totals, counts, sessions, "episode_h10")
    result["unique_tickers"] = len(names)
    result["repeat_observation_n"] = len(rows) - len(names)
    result["issuers_with_multiple_observations"] = sum(len(value) > 1 for value in by_name.values())
    intervals = []
    for date in dates:
        endpoints = {(r["entry_date"], r["exit_date"]) for r in by_date[date]}
        check(len(endpoints) == 1, "Same issuance date has varying horizon endpoints")
        entry, exit_date = next(iter(endpoints))
        intervals.append({"date": date, "entry": entry, "exit": exit_date,
                          "entry_index": sessions.index(entry), "exit_index": sessions.index(exit_date)})
    overlaps = []
    for left, right in itertools.combinations(intervals, 2):
        shared = max(0, min(left["exit_index"], right["exit_index"]) - max(left["entry_index"], right["entry_index"]))
        if shared:
            overlaps.append({"left": left["date"], "right": right["date"], "shared_return_sessions": shared})
    independent, end = [], -1
    for row in sorted(intervals, key=lambda r: (r["exit_index"], r["entry_index"])):
        if row["entry_index"] >= end:
            independent.append(row["date"])
            end = row["exit_index"]
    repeated_overlap = []
    for ticker, group in by_name.items():
        for a, b in itertools.combinations(sorted(group, key=lambda r: r["date"]), 2):
            overlap = max(0, min(sessions.index(a["exit_date"]), sessions.index(b["exit_date"])) - max(sessions.index(a["entry_date"]), sessions.index(b["entry_date"])))
            if overlap:
                repeated_overlap.append({"ticker": ticker, "left": a["date"], "right": b["date"], "shared_return_sessions": overlap})
    result["window_dependence"] = {"date_pair_n": math.comb(len(dates), 2), "overlapping_date_pair_n": len(overlaps),
                                    "overlapping_date_pairs": overlaps,
                                    "maximum_nonoverlapping_date_window_n": len(independent),
                                    "one_maximal_nonoverlapping_date_set": independent,
                                    "repeated_issuer_overlapping_pair_n": len(repeated_overlap),
                                    "repeated_issuer_overlapping_pairs": repeated_overlap,
                                    "interpretation": "Structural overlap counts; maximum disjoint windows is not an estimated statistical effective sample size."}
    origin = min(r["entry_index"] for r in intervals)
    phases = []
    for phase in range(10):
        chosen_dates = [r["date"] for r in intervals if (r["entry_index"] - origin) % 10 == phase]
        chosen = [r for r in rows if r["date"] in chosen_dates]
        phases.append({"phase": phase, "dates": chosen_dates, "date_n": len(chosen_dates), "episode_n": len(chosen),
                       "tickers": sorted({r["ticker"] for r in chosen}),
                       "mean_excess_pp": fmean(r["excess_cc"] for r in chosen) if chosen else None,
                       "positive_excess_fraction": fmean(r["excess_cc"] > 0 for r in chosen) if chosen else None})
    check(sum(r["episode_n"] for r in phases) == len(rows), "Thinning phases lost rows")
    result["all_ten_nonoverlapping_phases"] = phases
    overall, total = result["row_weighted_mean_pp"], sum(r["excess_cc"] for r in rows)
    leave_date = [{"date": date, "removed_n": len(group), "remaining_n": len(rows) - len(group),
                   "mean_without_pp": (total - sum(r["excess_cc"] for r in group)) / (len(rows) - len(group))} for date, group in by_date.items()]
    leave_name = [{"ticker": ticker, "removed_n": len(group), "remaining_n": len(rows) - len(group),
                   "mean_without_pp": (total - sum(r["excess_cc"] for r in group)) / (len(rows) - len(group))} for ticker, group in by_name.items()]
    for group in [leave_date, leave_name]:
        for row in group:
            row["mean_shift_pp"] = row["mean_without_pp"] - overall
        group.sort(key=lambda r: (-abs(r["mean_shift_pp"]), r.get("date", r.get("ticker"))))
    result["leave_one_date_out"] = leave_date
    result["leave_one_issuer_out"] = leave_name
    name_sum = np.array([sum(r["excess_cc"] for r in by_name[name]) for name in names])
    name_n = np.array([len(by_name[name]) for name in names])
    seed = stable_seed("episode_h10:issuer")
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(names), size=(REPLICATES, len(names)))
    issuer_weights = np.zeros((REPLICATES, len(names)), dtype=np.int16)
    np.add.at(issuer_weights, (np.repeat(np.arange(REPLICATES), len(names)), sampled.ravel()), 1)
    issuer_only = (issuer_weights @ name_sum) / (issuer_weights @ name_n)
    result["issuer_cluster_only"] = {"seed": seed, **distribution(issuer_only)}
    first, last = sessions.index(dates[0]), sessions.index(dates[-1])
    block_seed = stable_seed("episode_h10:two_way_block10")
    date_weights = calendar_block_weights(last - first + 1, 10, block_seed)
    date_indices = np.array([sessions.index(r["date"]) - first for r in rows])
    name_index = {name: i for i, name in enumerate(names)}
    name_indices = np.array([name_index[r["ticker"]] for r in rows])
    weights = date_weights[:, date_indices] * issuer_weights[:, name_indices]
    numerator = weights @ np.array([r["excess_cc"] for r in rows])
    denominator = weights.sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        two_way = numerator / denominator
    result["calendar_block10_times_issuer_multiplicity"] = {"calendar_seed": block_seed, "issuer_seed": seed, **distribution(two_way),
                                                           "interpretation": "Descriptive crossed-cluster sensitivity. Small date span and sparse repeated-issuer panel preclude a calibrated confidence claim."}
    return result


def paired_rank_dependence(rank_addendum, sessions):
    daily = rank_addendum["accepted_daily_reconstruction"]
    result = []
    for arm in [a for a in ARMS if a != "score_top6"]:
        original_arm = "intel_top6" if arm == "intended_intel_top6" else arm
        dates = [r["date"] for r in daily]
        values = [r["arms"][original_arm]["mean_excess_cc_pp"] - r["arms"]["score_top6"]["mean_excess_cc_pp"] for r in daily]
        sensitivity, _ = series_sensitivity(dates, values, [1] * len(values), sessions, "paired_arm:" + arm)
        sensitivity["arm"] = arm
        sensitivity["daily_difference_sd_pp"] = stdev(values)
        mean = fmean(values)
        sensitivity["leave_one_date_out"] = [{"date": date, "mean_without_pp": (sum(values) - value) / (len(values) - 1),
                                               "mean_shift_pp": (sum(values) - value) / (len(values) - 1) - mean}
                                              for date, value in zip(dates, values, strict=True)]
        result.append(sensitivity)
    return result


def power_planning(paired):
    normal = NormalDist()
    result = {"formula": "ceil(((z_0.975 + z_power) * sigma / (true_effect - hurdle)) ** 2)",
              "units": "Independent paired issuance-date equivalents under stated variance assumptions, never independent names.",
              "hurdle_pp": .25, "true_effect_equal_hurdle": "No finite sample size attains the target power because the margin is zero.",
              "arms": [], "limitations": ["The observed standard deviations use only eleven selected dates and are unstable.",
                                              "Dependence multipliers are scenarios, not estimates or calendar promises.",
                                              "The normal approximation omits variance-estimation uncertainty and sequential/multiplicity corrections.",
                                              "An observed block/IID ratio below one cannot justify shorter prospective evidence collection."]}
    for row in paired:
        sd = row["daily_difference_sd_pp"]
        grid = []
        for power in [.8, .9]:
            for scale in [.5, 1, 2]:
                for truth in [.5, .75, 1.0]:
                    required = math.ceil(((normal.inv_cdf(.975) + normal.inv_cdf(power)) * sd * scale / (truth - .25)) ** 2)
                    grid.append({"power": power, "sd_multiplier": scale, "assumed_sd_pp": sd * scale,
                                 "true_effect_pp": truth, "margin_above_hurdle_pp": truth - .25,
                                 "independent_date_equivalents": required,
                                 "illustrative_observed_date_requirements_by_dependence_multiplier": {str(multiplier): required * multiplier for multiplier in [1, 2, 5, 10]}})
        result["arms"].append({"arm": row["arm"], "observed_paired_daily_sd_pp": sd, "observed_mean_difference_pp": row["row_weighted_mean_pp"],
                               "date_n": row["n_dates"], "calendar_span": row["calendar_session_span"],
                               "detect_0.25_pp_vs_zero_at_80pct_iid_date_equivalents": math.ceil(((normal.inv_cdf(.975) + normal.inv_cdf(.8)) * sd / .25) ** 2),
                               "grid": grid})
    return result


def matching_self_test():
    graphs = [([3, 3, 1], 2), ([1, 1, 6, 6], 3), ([1, 2, 4], 3), ([1, 1, 2], 3), ([7, 3, 6, 5, 4], 3)]
    rng = random.Random(20261009)
    for _ in range(35):
        k = rng.randint(1, 4)
        graphs.append(([rng.randrange(1 << k) for _ in range(rng.randint(k, 7))], k))
    checked = []
    for allowed, k in graphs:
        enumerated = [assignment for assignment in itertools.permutations(range(len(allowed)), k)
                      if all(allowed[candidate] & (1 << slot) for slot, candidate in enumerate(assignment))]
        suffix = count_table(allowed, k)
        count = suffix[0][(1 << k) - 1]
        check(count == len(enumerated), "Exact count fails exhaustive test")
        values = [float(index - 2) for index in range(len(allowed))]
        ways, sums, squares = exact_total_moments(allowed, values, k)
        near(sums, sum(sum(values[i] for i in assignment) for assignment in enumerated), "First moment fails exhaustive test")
        near(squares, sum(sum(values[i] for i in assignment) ** 2 for assignment in enumerated), "Second moment fails exhaustive test")
        check(ways == count, "Moment count fails exhaustive test")
        if count:
            incidence = exact_inclusions(allowed, k, suffix)
            for candidate in range(len(allowed)):
                for slot in range(k):
                    check(incidence[candidate][slot] == sum(assignment[slot] == candidate for assignment in enumerated), "Marginal count fails exhaustive test")
            possible = set(enumerated)
            sampler = random.Random(919)
            for _ in range(50):
                check(tuple(sample_assignment(allowed, k, suffix, sampler)) in possible, "Sampler outputs inadmissible matching")
        checked.append({"allowed_masks": allowed, "slot_n": k, "full_assignments": count})
    # A concrete graph with all per-slot edges present and no full matching.
    hall = [3, 4]
    check(all(any(mask & (1 << s) for mask in hall) for s in range(3)), "Hall fixture missing individual edge")
    check(count_table(hall, 3)[0][7] == 0, "Hall fixture incorrectly called feasible")
    return {"status": "PASS", "exhaustive_graph_n": len(checked), "graphs": checked,
            "separate_hall_collision_fixture": {"allowed_masks": hall, "slot_n": 3, "per_slot_nonempty": True, "full_matching_count": 0}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docket", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    inputs, calendar = load_inputs(args.docket, args.out)
    evidence = inputs["historical_evidence.json"]["autopsy"]
    rank = inputs["rank_metrics_addendum.json"]
    pool = parse_pool(inputs["rank_metrics_pool_input.json"])
    self_test = matching_self_test()
    cases, cache, gates, exclusions = make_cases(pool, evidence, rank)
    frozen = {"source_sha": SOURCE_SHA, "design_sha256": DESIGN_SHA,
              "input_sha256": INPUT_HASHES, "calendar_input_sha256": CALENDAR_SHA,
              "date_gates": gates, "existing_vintage_exclusion_dates": exclusions,
              "vintage_exclusions_without_qualified_rows": sorted(set(exclusions) - {r["date"] for r in pool}),
              "cases": [frozen_receipt(case, cache[case["graph_key"]]) for case in cases],
              "statement": "Graph membership, edge counts and feasibility use only pre-outcome fields. This file is written before matching outcomes are graded."}
    frozen_bytes = (json.dumps(frozen, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    (args.out / "FROZEN_MATCHING_RECEIPT.json").write_bytes(frozen_bytes)
    print("Frozen pre-outcome graphs", len(cases), "unique", len(cache), "sha256", sha(frozen_bytes), flush=True)
    graph_outputs, graph_samples = {}, {}
    for i, (key, graph) in enumerate(sorted(cache.items())):
        graph_outputs[key], graph_samples[key] = graph_outcomes(graph, key)
        if (i + 1) % 20 == 0:
            print("Graded unique graph", i + 1, "of", len(cache), flush=True)
    graded = [grade_case(case, cache[case["graph_key"]], graph_outputs[case["graph_key"]]) for case in cases]
    aggregate, comparisons = matching_aggregates(graded, graph_outputs, graph_samples, calendar["sessions"])
    episode = episode_dependence(inputs["v4_review_rows.json"], evidence, calendar["sessions"])
    paired = paired_rank_dependence(rank, calendar["sessions"])
    output = {"schema": "cn_prophet_matched_controls_deepening_v1", "source_sha": SOURCE_SHA,
              "design_sha256": DESIGN_SHA, "script_sha256": sha(Path(__file__).read_bytes()),
              "input_sha256": INPUT_HASHES, "calendar_input_sha256": CALENDAR_SHA,
              "frozen_matching_receipt_sha256": sha(frozen_bytes), "base_seed": BASE_SEED, "replicates": REPLICATES,
              "matching_self_test": self_test, "matching_case_results": graded, "graph_outcome_results": graph_outputs,
              "matching_aggregates": aggregate, "common_support_comparisons": comparisons,
              "episode_dependence": episode, "paired_rank_dependence": paired, "power_planning": power_planning(paired),
              "verification": {"accepted_qualified_rows": 1488, "accepted_episode_rows": 288, "accepted_episode_dates": 21,
                                "accepted_common_feature_dates": 11, "all_55_original_arm_date_memberships_reconstructed": True,
                                "intended_intel_11_memberships_reconstructed": True, "original_17_date_82_of_102_slot_control_reproduced": True,
                                "immutable_input_hashes_pass": True, "no_new_price_or_return_grading": True},
              "limits": ["Conditional retrospective, current adjusted-price, gross close/close evidence only; no certified first-publication PIT or executable portfolio claims.",
                         "Uniform full slot assignments are not uniform unique unordered portfolios; sampling policy is explicit.",
                         "Matching support, missing labels and feature availability restrict comparisons and remain in denominators.",
                         "Randomization tail fractions are descriptive, not exchangeability-valid p-values.",
                         "Block/issuer intervals and power numbers are sensitivity/planning calculations, not calibrated small-sample guarantees.",
                         "No new alpha arm, block-size optimization or favorable threshold search was performed."]}
    payload = (json.dumps(output, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    (args.out / "MATCHED_CONTROLS_RESULTS.json").write_bytes(payload)
    print("DONE", args.out / "MATCHED_CONTROLS_RESULTS.json", "bytes", len(payload), "sha256", sha(payload), flush=True)
    print(json.dumps({"matching": [{k: r.get(k) for k in ["scope", "arm", "specification", "matured_pool_date_n", "matured_dates_all_slots_nonempty", "matured_dates_full_matching", "complete_date_n", "mean_selected_minus_expected_control_pp"]} for r in aggregate],
                      "episode": {k: episode[k] for k in ["row_weighted_mean_pp", "unique_tickers", "repeat_observation_n", "window_dependence"]}}, default=str)[:16000])


if __name__ == "__main__":
    main()
