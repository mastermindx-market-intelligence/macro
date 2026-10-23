#!/usr/bin/env python3
"""Independent graph oracle: recompute edges, augment paths and enumerate controls.

Does not import the analysis implementation. Exhaustively enumerates the nine
primary complete matching populations and the important missing-label graph.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
DOCKET = HERE.parents[1]


def check(value, message):
    if not value:
        raise AssertionError(message)


def near(a, b, message):
    check(math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-8), message)


def augmenting_path_size(neighbors):
    assigned = {}

    def augment(slot, seen):
        for candidate in neighbors[slot]:
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate not in assigned or augment(assigned[candidate], seen):
                assigned[candidate] = slot
                return True
        return False

    return sum(augment(slot, set()) for slot in range(len(neighbors)))


def partitions(items):
    """All set partitions, for the independent collision inclusion-exclusion."""
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for partition in partitions(rest):
        yield [[first]] + partition
        for i in range(len(partition)):
            yield partition[:i] + [[first] + partition[i]] + partition[i + 1:]


def component_count(neighbors):
    """Injective maps via set-partition inclusion-exclusion; k <= 4 in scope.

    This differs from the analysis candidate/slot-mask dynamic program.
    A block denotes slots constrained to collide on one alternative name.
    """
    k = len(neighbors)
    total = 0
    for partition in partitions(list(range(k))):
        term = (-1) ** (k - len(partition))
        for block in partition:
            shared = set.intersection(*(set(neighbors[i]) for i in block))
            term *= math.factorial(len(block) - 1) * len(shared)
        total += term
    return total


def enumerate_assignments(neighbors, rows):
    order = sorted(range(len(neighbors)), key=lambda slot: (len(neighbors[slot]), slot))
    count, observed_count = 0, 0
    value_sum, value_square = 0.0, 0.0
    inclusions = defaultdict(int)

    def visit(depth, used):
        nonlocal count, observed_count, value_sum, value_square
        if depth == len(order):
            count += 1
            for ticker in used:
                inclusions[ticker] += 1
            if all(rows[ticker]["status"] == "observed" for ticker in used):
                value = math.fsum(float(rows[ticker]["excess_cc"]) for ticker in used) / len(order)
                observed_count += 1
                value_sum += value
                value_square += value * value
            return
        for ticker in neighbors[order[depth]]:
            if ticker not in used:
                visit(depth + 1, used | {ticker})

    visit(0, set())
    return {"assignment_n": count, "observed_assignment_n": observed_count,
            "conditional_observed_mean_pp": value_sum / observed_count if observed_count else None,
            "conditional_observed_variance_pp2": value_square / observed_count - (value_sum / observed_count) ** 2 if observed_count else None,
            "inclusion_counts": dict(inclusions)}


def main():
    result = json.loads((HERE / "MATCHED_CONTROLS_RESULTS.json").read_text())
    frozen_bytes = (HERE / "FROZEN_MATCHING_RECEIPT.json").read_bytes()
    check(hashlib.sha256(frozen_bytes).hexdigest() == result["frozen_matching_receipt_sha256"], "Frozen receipt hash mismatch")
    check(hashlib.sha256((HERE / "analyze_matched_controls.py").read_bytes()).hexdigest() == result["script_sha256"], "Result/script mismatch")
    for name, expected in result["input_sha256"].items():
        check(hashlib.sha256((DOCKET / name).read_bytes()).hexdigest() == expected, "Original input changed")
    matrix = json.loads((DOCKET / "rank_metrics_pool_input.json").read_text())
    rows = [dict(zip(matrix["columns"], values, strict=True)) for values in matrix["data"]]
    keyed = {(r["date"], r["ticker"]): r for r in rows}
    cases = json.loads(frozen_bytes)["cases"]
    graded = {r["case_id"]: r for r in result["matching_case_results"]}
    checked_graphs, enumerated, factorized = 0, [], []
    for case in cases:
        original = set(case["selected_order"])
        check(len(original) == 6, "Selected names are not distinct")
        check(not original.intersection(r["ticker"] for r in case["alternatives"]), "Original selected name in controls")
        neighbors = [[] for _ in range(6)]
        for alternative in case["alternatives"]:
            source = keyed[(case["date"], alternative["ticker"])]
            check((source["sector"] or None) == alternative["sector"], "Alternative sector differs")
            source_adv = float(source["adv_yi"]) if source["adv_yi"] else None
            check(source_adv == alternative["adv_yi"], "Alternative ADV differs")
            mask = 0
            for slot, selected in enumerate(case["slots"]):
                source_selected = keyed[(case["date"], selected["ticker"])]
                check((source_selected["sector"] or None) == selected["sector"], "Selected sector differs")
                selected_adv = float(source_selected["adv_yi"]) if source_selected["adv_yi"] else None
                check(selected_adv == selected["adv_yi"], "Selected ADV differs")
                ok = bool(selected["sector"]) and alternative["sector"] == selected["sector"]
                if case["specification"] == "sector_adv_0.5_to_2":
                    ok = ok and source_adv is not None and selected_adv is not None and min(source_adv, selected_adv) > 0
                    ok = ok and .5 * selected_adv <= source_adv <= 2 * selected_adv
                if ok:
                    mask += 1 << slot
                    neighbors[slot].append(alternative["ticker"])
            check(mask == alternative["slot_mask"], "Graph edge differs from frozen decision fields")
        maximum = augmenting_path_size(neighbors)
        check(maximum == case["maximum_distinct_matching_size"], "Independent maximum matching differs")
        check((maximum == 6) == bool(case["full_assignment_count"]), "Independent feasibility differs")
        sectors = defaultdict(list)
        for slot, selected in enumerate(case["slots"]):
            sectors[selected["sector"]].append(slot)
        check(max(map(len, sectors.values())) <= 4, "Observed case violates assumed sector cap")
        parts = {str(sector): component_count([neighbors[slot] for slot in slots]) for sector, slots in sectors.items()}
        check(math.prod(parts.values()) == case["full_assignment_count"], "Independent sector-factorized assignment count differs")
        factorized.append({"case_id": case["case_id"], "component_assignment_counts": parts,
                           "largest_sector_slot_n": max(map(len, sectors.values())), "full_assignment_count": math.prod(parts.values())})
        checked_graphs += 1
        main_complete = (case["scope"] == "broad_qualified" and case["arm"] == "featured_top6"
                         and case["specification"] == "sector_adv_0.5_to_2"
                         and graded[case["case_id"]]["status"] == "complete_matched_comparison")
        missing_example = (case["scope"] == "accepted_common_features" and case["arm"] == "intel_top6"
                           and case["date"] == "2026-09-01" and case["specification"] == "sector_adv_0.5_to_2")
        if not (main_complete or missing_example):
            continue
        source_rows = {ticker: row for (date, ticker), row in keyed.items() if date == case["date"]}
        oracle = enumerate_assignments(neighbors, source_rows)
        check(oracle["assignment_n"] == case["full_assignment_count"], "Enumeration count differs from dynamic program")
        graph_result = result["graph_outcome_results"][graded[case["case_id"]]["graph_key"]]
        check(oracle["observed_assignment_n"] == graph_result["all_observed_assignment_count"], "Missing-label matching mass differs")
        actual_inclusions = {r["ticker"]: r["assignment_inclusion_count"] for r in graph_result["name_inclusions"]}
        check(actual_inclusions == oracle["inclusion_counts"], "Enumeration inclusion counts differ")
        if main_complete:
            near(oracle["conditional_observed_mean_pp"], graph_result["exact_expected_control_excess_pp"], "Enumeration expected return differs")
            near(oracle["conditional_observed_variance_pp2"], graph_result["exact_control_randomization_sd_pp"] ** 2, "Enumeration variance differs")
        enumerated.append({"case_id": case["case_id"], **oracle})
    check(len(enumerated) == 10, "Expected nine primary graphs plus one missing-label graph")
    out = {"status": "PASS", "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "analysis_sha256": result["script_sha256"], "result_sha256": hashlib.sha256((HERE / "MATCHED_CONTROLS_RESULTS.json").read_bytes()).hexdigest(),
           "all_frozen_edge_and_maximum_matching_checks": checked_graphs,
           "all_sector_factorized_count_checks": len(factorized),
           "sector_factorization": factorized,
           "exhaustively_enumerated_graphs": enumerated,
           "enumerated_assignment_total": sum(r["assignment_n"] for r in enumerated),
           "interpretation": "Independent computational oracle for graph construction, full matching, exact expectations and unresolved-label mass. It does not certify historical source vintages or small-sample inference."}
    (HERE / "VALIDATION.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: out[key] for key in ["status", "all_frozen_edge_and_maximum_matching_checks", "all_sector_factorized_count_checks", "enumerated_assignment_total"]}))


if __name__ == "__main__":
    main()
