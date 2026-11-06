"""Independent finite synthetic controls, not an application selector.

Reads only the named frozen scratch policies/receipts. All flow candidates,
values and action effects are invented toy inputs. No financial source,
application, native store, registry, trust interface or network is used.
"""
from collections import Counter, deque
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
from itertools import combinations, product
import json
from pathlib import Path

LANES = Path(__file__).resolve().parents[1]
V2 = LANES / "source_diagnostic_policy_v2"
V1 = LANES / "source_diagnostic_policy_v1"


def bind(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(LANES)), "bytes": len(raw),
            "sha256": sha256(raw).hexdigest()}


def pointer(obj, path):
    for key in path.lstrip("/").split("/"):
        obj = obj[key]
    return obj


def changed(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        result = []
        for k in sorted(set(a) | set(b)):
            child = path + "/" + k
            result.extend([child] if k not in a or k not in b
                          else changed(a[k], b[k], child))
        return result
    return [] if a == b else [path]


def maxflow(candidates, country, cells):
    """Small integral Edmonds-Karp implementation for artificial graphs."""
    assert all(type(v) is int and v >= 0 for v in (*country.values(), *cells.values()))
    capacity, adjacent = {}, {}

    def edge(a, b, value):
        capacity[a, b] = value
        capacity[b, a] = 0
        adjacent.setdefault(a, set()).add(b)
        adjacent.setdefault(b, set()).add(a)

    counts = Counter((c[1], c[2]) for c in candidates)
    for g, value in country.items():
        edge("source", "g:" + g, value)
    for g in country:
        for cell in cells:
            edge("g:" + g, "c:" + cell, counts[g, cell])
    for cell, value in cells.items():
        edge("c:" + cell, "sink", value)
    total = 0
    while True:
        parent, queue = {"source": None}, deque(["source"])
        while queue and "sink" not in parent:
            current = queue.popleft()
            for nxt in sorted(adjacent[current]):
                if nxt not in parent and capacity[current, nxt] > 0:
                    parent[nxt] = current
                    queue.append(nxt)
        if "sink" not in parent:
            return total
        amount, current = None, "sink"
        while parent[current] is not None:
            prior = parent[current]
            amount = capacity[prior, current] if amount is None else min(amount, capacity[prior, current])
            current = prior
        current = "sink"
        while parent[current] is not None:
            prior = parent[current]
            capacity[prior, current] -= amount
            capacity[current, prior] += amount
            current = prior
        total += amount


def exhaustive(candidates, country, cells):
    result = []
    for rows in combinations(candidates, sum(country.values())):
        gc, cc = Counter(r[1] for r in rows), Counter(r[2] for r in rows)
        if all(gc[k] == v for k, v in country.items()) and all(cc[k] == v for k, v in cells.items()):
            result.append(tuple(sorted(r[0] for r in rows)))
    return sorted(result)


def greedy(candidates, country, cells):
    assert len({c[0] for c in candidates}) == len(candidates)
    target = sum(country.values())
    assert target == sum(cells.values())
    if maxflow(candidates, country, cells) != target:
        return None
    ordered, remaining = sorted(candidates), sorted(candidates)
    gc, cc, selected = dict(country), dict(cells), []
    for row in ordered:
        remaining.remove(row)
        tg, tc = dict(gc), dict(cc)
        tg[row[1]] -= 1
        tc[row[2]] -= 1
        if any(v < 0 for v in (*tg.values(), *tc.values())):
            continue
        assert sum(tg.values()) == sum(tc.values())
        if maxflow(remaining, tg, tc) == sum(tg.values()):
            selected.append(row[0])
            gc, cc = tg, tc
        if len(selected) == target:
            break
    assert len(selected) == target and all(v == 0 for v in (*gc.values(), *cc.values()))
    return tuple(selected)


def bands(values):
    values = sorted(values, reverse=True)
    if not values:
        return {}
    n = len(values)
    t1, t2 = values[(n + 1) // 2 - 1], values[(3 * n + 3) // 4 - 1]
    return {str(v): "L" if v >= t1 else "M" if v >= t2 else "S" for v in values}


def main():
    bindings = [bind(p) for p in sorted(V2.iterdir()) if p.is_file()]
    assert len(bindings) == 10 and sum(b["bytes"] for b in bindings) == 183753
    assert next(b for b in bindings if b["path"].endswith("/RECOMMENDED_SELECTION_POLICY.json"))["sha256"] == "d41422d76219b1c5d3a3c9cbb19a1bc3124433031200b09499033bd4dc30d522"
    p1, p2 = (json.loads((p / "RECOMMENDED_SELECTION_POLICY.json").read_text()) for p in (V1, V2))
    validation = json.loads((V2 / "ARTIFACT_VALIDATION.json").read_text())
    for path in validation["preserved_equal_json_pointers"]:
        assert pointer(p1, path) == pointer(p2, path), path
    changes = changed(p1, p2)
    assert changes == validation["exact_v1_to_v2_changed_json_pointers"]
    manifest = json.loads((V2 / "PACKAGE_MANIFEST.json").read_text())
    for item in manifest["files"]:
        actual = bind(V2 / item["path"])
        assert actual["bytes"] == item["bytes"] and actual["sha256"] == item["sha256"]
    old = json.loads((V2 / "PRESERVATION_BASELINE.json").read_text())
    for item in old["files"]:
        assert bind(LANES / item["path"]) == item
    law = p2["preserved_law"]
    assert law["strata"] == ["US", "CN_MAINLAND", "HK", "CA", "INT"]
    assert law["total_issuers"] == 120 and law["issuer_count_per_stratum"] == 24
    assert len(law["groups"]) == 6 and law["issuer_count_per_stratum_group"] == 4
    assert law["quota_by_size_slot"] == {"L": 2, "M": 1, "S": 1}
    assert law["total_by_size_slot"] == {"L": 60, "M": 30, "S": 30}
    assert law["international_country_group_quotas"] == {"UK": 8, "JP": 8, "EU": 8}
    assert p2["relative_size"]["pool_count"] == 42
    assert p2["cutoff_policy"]["proposed_valuation_local_date"] == "2026-09-30"
    assert p2["cutoff_policy"]["public_knowledge_cutoff_utc"] == "2026-10-09T00:00:00Z"
    assert p2["cutoff_policy"]["actual_native_evidence_freeze_at_utc"] is None
    assert p2["deterministic_selection"]["seed_utf8"] == "GMI-WP02-20261009-v1"
    assert p2["authority_boundary"]["trust_interface_selected_here"] is None
    assert p2["holds"]["production_admission"] is False and p2["holds"]["predictive_admission"] is False

    countries, cells = {"J0": 1, "J1": 1, "J2": 1}, {"L": 2, "M": 1}
    matrix_count = feasible_count = 0
    for counts in product(range(3), repeat=6):
        rows = []
        for (g, cell), count in zip(product(countries, cells), counts):
            for i in range(count):
                rows.append((f"toy-{g}-{cell}-{i}", g, cell))
        brute = exhaustive(rows, countries, cells)
        value = maxflow(rows, countries, cells)
        assert (value == 3) == bool(brute)
        assert greedy(rows, countries, cells) == (brute[0] if brute else None)
        assert greedy(list(reversed(rows)), countries, cells) == (brute[0] if brute else None)
        matrix_count += 1
        feasible_count += bool(brute)
    assert matrix_count == 729
    assert maxflow([], {"J0": 0}, {"L": 0}) == 0
    assert maxflow([], {"J0": 1}, {"L": 1}) == 0
    try:
        greedy([("dup", "J0", "L"), ("dup", "J0", "L")], {"J0": 1}, {"L": 1})
    except AssertionError:
        duplicate_rejected = True
    else:
        raise AssertionError("toy duplicate identity was accepted")

    original, later = bands([500, 400, 300, 200, 100]), bands([500, 400, 300, 200])
    assert original["300"] == "L" and later["300"] == "M"
    assert original["200"] == "M" and later["200"] == "S"
    assert bands([4, 3, 3, 1]) == {"4": "L", "3": "L", "1": "S"}
    base, retirement, price = Fraction(100000000), Fraction(-10000000), Fraction(20)
    signed_value, sign_erased_value = (base + retirement) * price, (base + abs(retirement)) * price
    assert signed_value == 1800000000 and sign_erased_value == 2200000000
    assert signed_value < 2000000000 <= sign_erased_value
    assert retirement < 0  # A literal positive-input validator would refuse it.

    assert bindings == [bind(p) for p in sorted(V2.iterdir()) if p.is_file()]
    return {
        "schema": "research.gmi.wp02.independent_corrective_method_checks/v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "result": "PASS_FINITE_SYNTHETIC_AND_BINDING_CONTROLS_ONLY",
        "frozen_inputs": bindings,
        "input_bytes": 183753,
        "unchanged_prior_files_rehashed": len(old["files"]),
        "equal_policy_pointer_count": len(validation["preserved_equal_json_pointers"]),
        "changed_policy_pointers": changes,
        "exact_quota_date_seed_checks": "PASS",
        "synthetic_flow": {
            "algorithm": "Independent Edmonds-Karp plus residual greedy compared with exhaustive subsets",
            "country_count": 3, "cell_count": 2,
            "capacities_per_intersection": [0, 1, 2],
            "matrices_tested": matrix_count, "feasible": feasible_count,
            "infeasible": matrix_count - feasible_count,
            "priority": "Fixed artificial identifier lexical order, not real owner IDs",
            "input_orders_per_matrix": 2,
            "duplicate_toy_identity_rejected": duplicate_rejected,
            "zero_residual_target_tested": True,
            "maximum_candidate_count": 12,
            "production_or_full_18_cell_solver_tested": False
        },
        "roster_counterexample_reproduced": True,
        "equal_value_boundary_block_preserved": True,
        "signed_action_counterexample": {
            "base_shares": "100000000", "signed_retirement": "-10000000",
            "price": "20", "correct_cap": str(signed_value),
            "wrong_abs_delta_cap": str(sign_erased_value),
            "crosses_absolute_2b_boundary": True,
            "negative_action_is_not_a_negative_price_or_cap_factor": True,
            "example_is_synthetic": True
        },
        "proof_limits": {
            "actual_population_count": None, "actual_INT_flow": None,
            "production_selector_implemented_or_run": False,
            "source_receipt_validator_or_trust_adapter_run": False,
            "real_source_or_entitlement_verified": False,
            "native_app_Git_or_source_acquisition_effects": False,
            "policy_adoption": False, "prediction_or_production_admission": False,
            "input_files_changed": False
        }
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))
