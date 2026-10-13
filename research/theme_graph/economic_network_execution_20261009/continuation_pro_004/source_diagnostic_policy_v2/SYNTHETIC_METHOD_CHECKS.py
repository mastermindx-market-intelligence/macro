"""Synthetic arithmetic/set/feasibility controls for the WP02 v2 method correction.

NOT a production selector, input-receipt validator, source-proof verifier or
issuer dataset. Every ID/value is artificial. Supersession edges below are
prevalidated logical premises for the examples; this script cannot verify a
publisher correction or make a boolean/digest stand for real source evidence.
Only standard-library code and embedded synthetic inputs are used.
"""
from collections import Counter
from fractions import Fraction
from itertools import combinations, permutations
import json

def bands(values):
    v = sorted(values, reverse=True)
    if not v:
        return {}
    t1 = v[(len(v) + 1) // 2 - 1]
    t2 = v[(3 * len(v) + 3) // 4 - 1]
    return {str(x): "L" if x >= t1 else "M" if x >= t2 else "S" for x in v}

def transition(roster, event, reverse=False):
    result = dict(roster)
    key, before, after, kind = event
    if kind == "ADMIT":
        assert before is None and after is not None
    elif kind == "REMOVE":
        assert before is not None and after is None
    elif kind == "CHANGE":
        assert before is not None and after is not None
    else:
        raise ValueError(kind)
    expected, replacement = (after, before) if reverse else (before, after)
    assert result.get(key) == expected, "before/after state mismatch"
    if replacement is None:
        result.pop(key, None)
    else:
        result[key] = replacement
    return result

def point_value(assertions, proved_edges=()):
    # All examples concern ONE synthetic economic class and actual-share basis.
    # Date strings are fixed-format ISO dates; source proof is outside this helper.
    eligible = [a for a in assertions if a["measure"] <= "2026-09-30"
                and a["published"] <= "2026-10-09"]
    if not eligible:
        return {"state": "UNAVAILABLE", "value": None, "active": []}
    latest = max(a["measure"] for a in eligible)
    group = {a["id"]: a for a in eligible if a["measure"] == latest}
    outgoing = {key: set() for key in group}
    for newer, older in proved_edges:
        assert newer in group and older in group
        outgoing[newer].add(older)
    def visit(key, stack, done):
        assert key not in stack, "cyclic supersession"
        if key in done:
            return
        for child in outgoing[key]:
            visit(child, stack | {key}, done)
        done.add(key)
    done = set()
    for key in group:
        visit(key, set(), done)
    removed = {old for _, old in proved_edges}
    active = {key: a for key, a in group.items() if key not in removed}
    values = {Fraction(a["value"]) * Fraction(a.get("scale", 1))
              for a in active.values()}
    if len(values) > 1:
        return {"state": "CAP_COMPONENT_CONFLICT", "value": None,
                "active": sorted(active)}
    if not values:
        return {"state": "UNAVAILABLE", "value": None, "active": []}
    value = next(iter(values))
    return {"state": "RESOLVED", "value": str(value), "active": sorted(active)}

def completions(candidates, country, cell):
    if min([0] + list(country.values()) + list(cell.values())) < 0:
        return []
    target = sum(country.values())
    assert target == sum(cell.values())
    feasible = []
    for chosen in combinations(candidates, target):
        gc, cc = Counter(x[1] for x in chosen), Counter(x[2] for x in chosen)
        if all(gc.get(k, 0) == v for k, v in country.items()) and all(
                cc.get(k, 0) == v for k, v in cell.items()):
            feasible.append(chosen)
    return feasible

def synthetic_priority_selection(candidates, country, cell):
    assert len({x[0] for x in candidates}) == len(candidates), "duplicate toy ID"
    ordered = sorted(candidates)
    assert completions(ordered, country, cell), "initial infeasibility"
    total = sum(country.values())
    remaining, selected, targets = list(ordered), [], []
    country, cell = dict(country), dict(cell)
    for c in ordered:
        remaining.remove(c)  # Removal precedes the trial.
        tc, ts = dict(country), dict(cell)
        tc[c[1]] -= 1
        ts[c[2]] -= 1
        if min(list(tc.values()) + list(ts.values())) < 0:
            continue
        target = sum(tc.values())
        assert target == sum(ts.values())
        if completions(remaining, tc, ts):
            selected.append(c)
            targets.append(target)
            country, cell = tc, ts
        if len(selected) == total:
            break
    assert len(selected) == total
    assert all(x == 0 for x in list(country.values()) + list(cell.values()))
    return [x[0] for x in selected], targets

def main():
    checks = {}
    target = {"toy_A": 500, "toy_B": 400, "toy_C": 300, "toy_D": 200,
              "toy_E": 100}
    survivors = {k: v for k, v in target.items() if k != "toy_E"}
    assert bands(target.values())["300"] == "L"
    assert bands(survivors.values())["300"] == "M"
    assert bands(target.values())["200"] == "M"
    assert bands(survivors.values())["200"] == "S"
    checks["R1_survivor_roster_changes_quantiles"] = {
        "pass": True, "D_count": 5, "later_survivors": 4,
        "D_bands": bands(target.values()), "survivor_bands": bands(survivors.values())}
    events = [("toy_E", 100, None, "REMOVE"), ("toy_F", None, 600, "ADMIT")]
    anchor = dict(target)
    for event in events:
        anchor = transition(anchor, event)
    reconstructed = dict(anchor)
    for event in reversed(events):
        reconstructed = transition(reconstructed, event, reverse=True)
    assert reconstructed == target
    assert len(anchor) == len(target) and set(anchor) != set(target)
    checks["R1_reverse_and_forward_exact_sets"] = {
        "pass": True, "restored_post_D_removal": "toy_E",
        "removed_post_D_admission": "toy_F", "equal_counts_alone_insufficient": True}
    try:
        transition(anchor, ("toy_F", None, 999, "ADMIT"), reverse=True)
    except AssertionError:
        checks["R1_mismatched_event_state_rejected"] = {"pass": True}
    else:
        raise AssertionError("bad event accepted")

    a = {"id": "a", "measure": "2026-09-30", "published": "2026-10-01",
         "value": 190000000}
    b = {"id": "b", "measure": "2026-09-30", "published": "2026-10-08",
         "value": 210000000}
    conflict = point_value([a, b])
    assert conflict["state"] == "CAP_COMPONENT_CONFLICT" and conflict["value"] is None
    checks["R2_newer_publication_is_not_correction"] = {
        "pass": True, "result": conflict,
        "possible_reference_caps": [1900000000, 2100000000],
        "relative_1900m": bands([10000000000, 3000000000, 2000000000,
                               1900000000, 1000000000])["1900000000"],
        "relative_2100m": bands([10000000000, 3000000000, 2100000000,
                               2000000000, 1000000000])["2100000000"]}
    corrected = point_value([a, b], [("b", "a")])
    assert corrected["value"] == "210000000" and corrected["active"] == ["b"]
    independent = dict(a, id="independent")
    assert point_value([a, b, independent], [("b", "a")])["state"] == "CAP_COMPONENT_CONFLICT"
    checks["R2_scope_of_proved_supersession"] = {
        "pass": True, "with_proved_edge": corrected,
        "unreconciled_independent_assertion_still_conflicts": True,
        "real_source_supersession_verified": False}
    older = dict(a, id="older", measure="2026-06-30", published="2026-10-08",
                 value=999000000)
    newer = dict(b, id="newer", published="2026-10-01")
    assert point_value([older, newer])["value"] == "210000000"
    assert point_value([older, a, b])["state"] == "CAP_COMPONENT_CONFLICT"
    checks["R2_measurement_order_and_no_older_fallback"] = {"pass": True}
    scaled = dict(a, id="scaled", value=190, scale=1000000)
    assert point_value([a, scaled])["value"] == "190000000"
    assert len(point_value([a, scaled])["active"]) == 2
    checks["R2_exact_unit_equivalence"] = {"pass": True}
    try:
        point_value([a, b], [("b", "a"), ("a", "b")])
    except AssertionError:
        checks["R2_cyclic_revision_rejected"] = {"pass": True}
    else:
        raise AssertionError("cycle accepted")
    raw_price, old_shares, split = Fraction(10), Fraction(100), Fraction(2)
    new_shares = old_shares * split
    equivalent_price = raw_price / split
    assert equivalent_price * new_shares == raw_price * old_shares
    assert raw_price * new_shares != raw_price * old_shares
    checks["R2_stale_price_share_unit_bridge"] = {
        "pass": True, "before_and_corrected_value": "1000", "unbridged_value": "2000"}

    toy = [(0, "J0", "L"), (1, "J1", "L"), (2, "J2", "L"),
           (3, "J0", "M"), (4, "J1", "M"), (5, "J2", "M")]
    country, cell = {"J0": 1, "J1": 1, "J2": 1}, {"L": 2, "M": 1}
    brute = min([sorted(x[0] for x in subset)
                 for subset in completions(toy, country, cell)])
    chosen, residual_targets = synthetic_priority_selection(toy, country, cell)
    assert chosen == brute == [0, 1, 5] and residual_targets == [2, 1, 0]
    count = 0
    for perm in permutations(toy):
        assert synthetic_priority_selection(perm, country, cell)[0] == brute
        count += 1
    checks["INT_residual_procedure_vs_bruteforce"] = {
        "pass": True, "toy_selected_priorities": chosen,
        "residual_targets": residual_targets, "input_permutations": count,
        "actual_INT_solver_or_population": False}
    # Isolated residual subproblem, not a full initially feasible cohort.
    current = (0, "J0", "L")
    assert completions([current], {"J0": 1}, {"L": 1})
    assert not completions([], {"J0": 1}, {"L": 1})
    assert completions([], {"J0": 0}, {"L": 0}) == [()]
    checks["INT_isolated_self_use_and_zero_target"] = {
        "pass": True, "current_candidate_must_not_remain": True,
        "scope": "ISOLATED_RESIDUAL_SUBPROBLEM"}
    try:
        synthetic_priority_selection(toy + [toy[0]], country, cell)
    except AssertionError:
        checks["INT_duplicate_toy_identity_rejected"] = {"pass": True}
    else:
        raise AssertionError("duplicate accepted")

    return {
        "schema": "research.gmi.wp02.synthetic_correction_checks/v2",
        "result": "PASS_SYNTHETIC_CONTROLS_ONLY",
        "check_count": len(checks), "checks": checks,
        "real_issuer_inputs": False, "actual_selector_run": False,
        "source_receipt_validator_implemented": False,
        "real_source_proof_or_entitlement_verified": False,
        "actual_population_count": None, "actual_INT_flow": None,
        "application_or_native_effects": False,
        "limits": "Embedded synthetic arithmetic, reversible set transitions and small exhaustive feasibility only. No actual historical-source completeness or publisher-supersession evidence was tested."
    }

if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))

