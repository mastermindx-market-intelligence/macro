"""Independent expected outcomes for the bounded WP02 artificial research model.

No real source, provider, registry, network or financial population is used.
Tiny quota oracles enumerate subsets directly rather than reproducing maxflow.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import importlib.util
from itertools import combinations
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys

import inspect
import tempfile
import unittest
from unittest import mock


def cases(names, values):
    """Expand explicit data cases into ordinary unittest.TestCase methods."""
    def decorate(function):
        function._cases = (names.split(","), values)
        return function
    return decorate


assert_raises = unittest.TestCase().assertRaisesRegex


HERE = Path(__file__).resolve().parent
KERNEL_DIR = HERE if (HERE / "source_diagnostic.py").is_file() else HERE.parent / (
    "research/theme_graph/economic_network_execution_20261009/continuation_pro_004/source_diagnostic_kernel_v1")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


kernel = load("wp02_source_diagnostic_under_test", KERNEL_DIR / "source_diagnostic.py")
factory = load("wp02_artificial_example_writer", KERNEL_DIR / "synthetic_example.py")
POLICY = (KERNEL_DIR.parent / "source_diagnostic_policy_v2/RECOMMENDED_SELECTION_POLICY.json").read_bytes()
ADOPTION = (KERNEL_DIR.parent / "source_diagnostic_policy_adoption_v1/POLICY_ADOPTION.json").read_bytes()


def run(request):
    return kernel.diagnose(factory.encode(request), policy_bytes=POLICY, adoption_bytes=ADOPTION)


def codes(result):
    return {r["code"] for r in result["holds"]}


def rational_value(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def first_cap(result, request):
    issuer = request["records"][0]["issuer_id"]
    return next(row for row in result["synthetic"]["modeled_cap_receipts"] if row["issuer_id"] == issuer)


def assert_real_hold(result):
    assert result["status"] == "STRUCTURAL_ONLY"
    assert result["readiness"] == "NOT_READY"
    assert result["actual_F"] is None
    assert all(value is None for value in result["real_inputs"].values())
    assert result["authority"]["admission"] == "NOT_ADMITTED"
    assert all(value is False for key, value in result["authority"].items() if key != "admission")
    assert result["axes"]["source_authority_verification_state"] == "SOURCE_AUTHORITY_UNVERIFIED"
    assert result["axes"]["historical_coverage_verification_state"] == "FRAME_HISTORY_UNPROVEN"
    assert result["axes"]["entitlement_verification_state"] == "SOURCE_RIGHTS_UNVERIFIED"
    assert "SOURCE_USE_NOT_ENTITLED" not in codes(result)


def assert_no_quantiles(result):
    assert_real_hold(result)
    if result["synthetic"] is not None:
        assert result["synthetic"]["modeled_reference_pools"] is None
        assert result["synthetic"]["selection"] is None


def set_assertion(request, assertion, value=None, **updates):
    if value is not None:
        assertion["value"] = value
        assertion["evidence"] = factory.source(request, value)
    assertion.update(updates)


def independent_priority(issuer):
    parts = ["issuer-priority", "GMI-WP02-20261009-v1", issuer]
    payload = b"".join(struct.pack(">Q", len(s.encode("utf-8"))) + s.encode("utf-8") for s in parts)
    return sha256(payload).digest(), issuer.encode("utf-8")


def feasible_subsets(rows, country, cells):
    """A direct finite oracle: no graph, augmenting path or greedy completion."""
    target = sum(country.values())
    answers = []
    for group in combinations(rows, target):
        if Counter(r["country"] for r in group) == Counter(country) and \
                Counter(r["cell"] for r in group) == Counter(cells):
            answers.append(sorted((r["issuer_id"] for r in group), key=independent_priority))
    return sorted(answers, key=lambda selected: [independent_priority(s) for s in selected])


def maximum_partial_subset(rows, country, cells):
    for size in range(min(len(rows), sum(country.values())), -1, -1):
        for group in combinations(rows, size):
            cc, sc = Counter(r["country"] for r in group), Counter(r["cell"] for r in group)
            if all(cc[c] <= n for c, n in country.items()) and all(sc[c] <= n for c, n in cells.items()):
                return size
    raise AssertionError("empty subset must be feasible")


def test_exact_policy_sidecar_and_only_numeric_override():
    bound = kernel.bind_policy(POLICY, ADOPTION)
    assert bound["changed_pointer"] == "/capitalization/numeric_rule"
    assert bound["effective_policy_content_sha256"] == "90bec6078348af6e41c9538e12e0443dd37d671c85a7089c64c547f5ce5e7714"
    for policy, sidecar in ((POLICY + b"\n", ADOPTION), (POLICY, ADOPTION[:-1] + b" ")):
        result = kernel.diagnose(b"{}", policy_bytes=policy, adoption_bytes=sidecar)
        assert "FROZEN_POLICY_BINDING_MISMATCH" in codes(result)
        assert_real_hold(result)
    rewritten = factory.encode(json.loads(POLICY))
    assert rewritten != POLICY
    with assert_raises(kernel.ContractError, "FROZEN_POLICY_BINDING_MISMATCH"):
        kernel.bind_policy(rewritten, ADOPTION)


def test_complete_42_pool_fixture_has_exact_120_unique_and_every_quota(request_value):
    result = run(request_value)
    assert_real_hold(result)
    assert result["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    model = result["synthetic"]
    assert model["modeled_population_count"] == 168
    assert len(model["modeled_reference_pools"]) == 42
    assert all(row["modeled_N"] == 4 and row["band_counts"] == {"L": 2, "M": 1, "S": 1}
               for row in model["modeled_reference_pools"])
    lookup = {r["issuer_id"]: r for r in model["modeled_candidates"]}
    selected = model["selection"]["selected_issuer_ids"]
    assert len(selected) == len(set(selected)) == 120
    strata, activities, cells, int_countries = Counter(), Counter(), Counter(), Counter()
    for issuer in selected:
        row = lookup[issuer]
        s = row["country"] if row["country"] in ("US", "CN_MAINLAND", "HK", "CA") else "INT"
        strata[s] += 1
        activities[s, row["activity"]] += 1
        cells[s, row["activity"], row["band"]] += 1
        if s == "INT":
            int_countries[row["country"]] += 1
    assert strata == Counter({s: 24 for s in ("US", "CN_MAINLAND", "HK", "CA", "INT")})
    assert len(activities) == 30 and set(activities.values()) == {4}
    assert len(cells) == 90
    assert all(n == (2 if b == "L" else 1) for (_, _, b), n in cells.items())
    assert int_countries == Counter({"UK": 8, "JP": 8, "EU": 8})
    assert all(r["absolute_band"] == "MICRO" for r in model["modeled_candidates"])
    assert model["selection"]["INT"]["initial_flow"]["target"] == 24
    assert result["stress_cases"]["actual_genuine_case_count"] is None
    assert result["stress_cases"]["modeled_shortfall_per_stratum"] == {s: 6 for s in strata}


def test_same_bytes_deterministic_and_permutations_preserve_selection(request_value):
    baseline = run(request_value)
    assert kernel.canonical_bytes(run(request_value)) == kernel.canonical_bytes(baseline)
    shuffled = deepcopy(request_value)
    rng = random.Random(90311)
    rng.shuffle(shuffled["records"])
    rng.shuffle(shuffled["sources"])
    for field in ("anchor_members", "target_members", "expected_anchor_member_ids", "expected_target_member_ids", "partitions", "declared_partition_ids", "covered_event_kinds"):
        rng.shuffle(shuffled["history"][field])
    factory.bind_history_sources(shuffled)
    changed = run(shuffled)
    assert changed["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    assert baseline["request_binding"] != changed["request_binding"]
    for field in ("selection", "modeled_candidates", "modeled_reference_pools"):
        assert baseline["synthetic"][field] == changed["synthetic"][field]


def test_all_256_small_bipartite_candidate_sets_against_subset_oracle():
    all_rows = [{"issuer_id": "tiny-" + str(i), "country": country, "cell": cell}
                for i, (country, cell) in enumerate((c, s) for c in ("A", "B")
                                                   for s in ("X", "Y") for _ in range(2))]
    countries, cells = {"A": 2, "B": 2}, {"X": 2, "Y": 2}
    for mask in range(256):
        rows = [row for i, row in enumerate(all_rows) if mask & (1 << i)]
        expected = feasible_subsets(rows, countries, cells)
        actual = kernel.lexicographic_selection(rows, countries, cells)
        maximum = maximum_partial_subset(rows, countries, cells)
        assert actual["initial_flow"]["achieved_flow"] == maximum
        assert actual["selected_issuer_ids"] == (expected[0] if expected else None)
        reverse = kernel.lexicographic_selection(list(reversed(rows)), countries, cells)
        assert actual == reverse
        if not expected:
            cut = actual["initial_flow"]["deficient_cut"]
            assert cut["capacity"] == sum(e["capacity"] for e in cut["edges"]) == maximum


def test_full_18_cell_hall_failure_despite_every_marginal_passing():
    activities = ("SEMICONDUCTOR_CLOUD", "INDUSTRIALS", "CONSUMER", "ENERGY_MATERIALS", "FINANCIALS", "HEALTHCARE")
    demands = {a + "|" + b: 2 if b == "L" else 1 for a in activities for b in ("L", "M", "S")}
    first = activities[0] + "|L"
    rows = [{"issuer_id": "UK-" + str(i), "country": "UK", "cell": first} for i in range(8)]
    rows += [{"issuer_id": c + "-" + cell, "country": c, "cell": cell}
             for c in ("JP", "EU") for cell in demands]
    assert all(sum(r["country"] == c for r in rows) >= 8 for c in ("UK", "JP", "EU"))
    assert all(sum(r["cell"] == cell for r in rows) >= q for cell, q in demands.items())
    result = kernel.lexicographic_selection(rows, {"UK": 8, "JP": 8, "EU": 8}, demands)
    assert result["selected_issuer_ids"] is None
    assert result["initial_flow"]["achieved_flow"] == 18  # UK can contribute only two; others at most eight each.
    cut = result["initial_flow"]["deficient_cut"]
    assert cut["capacity"] == 18 and cut["deficit"] == 6
    assert "UK" in cut["reachable_countries"]


def test_zero_case_decreasing_trial_targets_and_current_removed():
    assert kernel.lexicographic_selection([], {"A": 0}, {"X": 0})["selected_issuer_ids"] == []
    rows = [{"issuer_id": "one-" + str(i), "country": "A", "cell": "X"} for i in range(3)]
    actual_flow = kernel.capacity_flow
    seen = []

    def observing_flow(candidates, countries, cells):
        seen.append(([r["issuer_id"] for r in candidates], sum(countries.values())))
        return actual_flow(candidates, countries, cells)

    with mock.patch.object(kernel, "capacity_flow", observing_flow):
        result = kernel.lexicographic_selection(rows, {"A": 2}, {"X": 2})
    ordered = sorted((r["issuer_id"] for r in rows), key=independent_priority)
    assert result["selected_issuer_ids"] == ordered[:2]
    assert seen[1:] == [(ordered[1:], 1), (ordered[2:], 0)]
    assert [r["remaining_target"] for r in result["trials"] if r["decision"] == "INCLUDE"] == [1, 0]


def test_priority_uses_exact_utf8_and_domain_lengths():
    for issuer in (" A ", "A", "é", "e\u0301", "Issuer:東京"):
        assert kernel.priority_hash("issuer-priority", issuer) == independent_priority(issuer)[0]
    assert kernel.priority_hash("issuer-priority", "é") != kernel.priority_hash("issuer-priority", "e\u0301")
    assert kernel.priority_hash("x", "ab", "c") != kernel.priority_hash("x", "a", "bc")


def test_tied_boundary_block_never_split_to_fill_quota(request_value):
    for r in request_value["records"][:4]:
        set_assertion(request_value, r["classes"][0]["price"]["assertions"][0], "1")
    result = run(request_value)
    pool = next(r for r in result["synthetic"]["modeled_reference_pools"] if r["country"] == "US" and r["activity"] == "SEMICONDUCTOR_CLOUD")
    assert pool["band_counts"] == {"L": 4, "M": 0, "S": 0}
    assert result["synthetic"]["selection"]["selected_issuer_ids"] is None
    assert "MODEL_QUOTA_INFEASIBLE" in codes(result)


@cases("size", [0, 1, 2, 3])
def test_empty_and_short_pools_do_not_relax_quota(size):
    result = run(factory.make_request(size))
    assert_real_hold(result)
    pools = result["synthetic"]["modeled_reference_pools"]
    assert len(pools) == 42 and all(row["modeled_N"] == size for row in pools)
    if size == 0:
        assert all(row["t1"] is None and row["t2"] is None for row in pools)
    assert result["synthetic"]["selection"]["selected_issuer_ids"] is None


def test_duplicate_identity_across_pools_refuses_before_aggregation(request_value):
    request_value["records"][24]["issuer_id"] = request_value["records"][0]["issuer_id"]
    factory.refresh_counts(request_value)
    result = run(request_value)
    assert "DUPLICATE_ECONOMIC_ISSUER" in codes(result)
    assert_no_quantiles(result)


def test_unresolved_or_missing_cap_record_is_retained_not_dropped(request_value):
    request_value["records"][0]["issuer_id"] = None
    factory.refresh_counts(request_value)
    result = run(request_value)
    assert "POTENTIALLY_ELIGIBLE_RECORD_UNRESOLVED" in codes(result)
    assert_no_quantiles(result)
    assert result["supplied_counts"]["unresolved_potentially_eligible_count"]["supplied_value"] == 1


def test_current_survivor_list_held_even_when_all_receipt_claims_true(request_value):
    request_value["history"]["kind"] = "CURRENT_ONLY"
    request_value["claims"] = {"producer_success": True, "source_authority_verified": True, "history_proven": True,
                               "rights_verified": True, "owner_id": "trusted-looking-owner",
                               "receipt_sha256": "a" * 64, "source_path": "/retained/complete", "actual_F": "2026-10-09T13:00:00Z"}
    result = run(request_value)
    assert "CURRENT_ONLY_SURVIVOR_FRAME" in codes(result)
    assert_no_quantiles(result)


def test_equal_counts_with_offset_missing_extra_members_fail_exact_sets(request_value):
    h = request_value["history"]
    h["target_members"][0]["member_id"] = "ARTIFICIAL:GHOST_REPLACEMENT"
    h["expected_target_member_ids"][0] = "ARTIFICIAL:GHOST_REPLACEMENT"
    factory.bind_history_sources(request_value)
    factory.refresh_counts(request_value)
    result = run(request_value)
    assert "TARGET_MEMBER_SET_MISMATCH" in codes(result)
    assert all(r.get("reconciliation") != "MISMATCH" for r in result["supplied_counts"].values())
    diff = result["synthetic"]["modeled_history"]["set_difference"]
    assert len(diff["missing"]) == len(diff["extra"]) == 1
    assert_no_quantiles(result)


def removal_reconstruction(request):
    h = request["history"]
    removed = h["anchor_members"].pop(0)
    h.update({"kind": "RECONSTRUCTION", "anchor_date": "2026-10-01", "anchor_public_upper": "2026-10-02T00:00:00Z",
              "coverage_start": "2026-09-30", "coverage_end": "2026-10-01",
              "events": [{"event_id": "POST_D_REMOVAL", "effective_date": "2026-10-01", "sequence": 1,
                          "kind": "REMOVAL", "public_upper": "2026-10-02T00:00:00Z", "before": [removed], "after": []}],
              "declared_event_ids": ["POST_D_REMOVAL"],
              "expected_anchor_member_ids": [m["member_id"] for m in h["anchor_members"]]})
    factory.bind_history_sources(request)
    factory.refresh_counts(request)


def test_reverse_reconstruction_restores_delisted_member_and_original_selection(request_value):
    baseline = run(request_value)
    removal_reconstruction(request_value)
    result = run(request_value)
    assert result["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    history = result["synthetic"]["modeled_history"]
    assert history["direction"] == "REVERSE" and history["anchor_supplied_count"] == 167
    assert history["reconstructed_model_count"] == 168
    assert result["synthetic"]["selection"] == baseline["synthetic"]["selection"]


def test_forward_reconstruction_validates_before_state_and_exact_target(request_value):
    h = request_value["history"]
    added = h["anchor_members"].pop(0)
    h.update({"kind": "RECONSTRUCTION", "anchor_date": "2026-09-29", "coverage_start": "2026-09-29",
              "events": [{"event_id": "D_ADMISSION", "effective_date": "2026-09-30", "sequence": 1,
                          "kind": "ADMISSION", "public_upper": "2026-10-01T00:00:00Z", "before": [], "after": [added]}],
              "declared_event_ids": ["D_ADMISSION"],
              "expected_anchor_member_ids": [m["member_id"] for m in h["anchor_members"]]})
    factory.bind_history_sources(request_value)
    factory.refresh_counts(request_value)
    result = run(request_value)
    assert result["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    assert result["synthetic"]["modeled_history"]["direction"] == "FORWARD"


def test_reverse_event_after_state_mismatch_cannot_pass_count_controls(request_value):
    h = request_value["history"]
    old = dict(h["target_members"][0])
    after = dict(old, partition_id="ARTIFICIAL_PARTITION:UK")
    h["anchor_members"][0] = dict(after, partition_id="ARTIFICIAL_PARTITION:EU")
    h.update({"kind": "RECONSTRUCTION", "anchor_date": "2026-10-01", "anchor_public_upper": "2026-10-02T00:00:00Z",
              "coverage_start": "2026-09-30", "coverage_end": "2026-10-01",
              "events": [{"event_id": "TRANSFER", "effective_date": "2026-10-01", "sequence": 1, "kind": "TRANSFER",
                          "public_upper": "2026-10-02T00:00:00Z", "before": [old], "after": [after]}],
              "declared_event_ids": ["TRANSFER"]})
    factory.bind_history_sources(request_value)
    factory.refresh_counts(request_value)
    result = run(request_value)
    assert "EVENT_BEFORE_AFTER_STATE_MISMATCH" in codes(result)
    assert_no_quantiles(result)


@cases("mutation,expected", [
    ("post_k", "POST_CUTOFF_ANCHOR"), ("missing_kind", "EVENT_KIND_UNCOVERED"),
    ("raw_mismatch", "RAW_TO_PARSED_RECONCILIATION_MISMATCH"),
    ("duplicate_order", "AMBIGUOUS_EVENT_ID_OR_ORDER")])
def test_reconstruction_failures_are_not_repaired_by_flags(request_value, mutation, expected):
    removal_reconstruction(request_value)
    h = request_value["history"]
    if mutation == "post_k":
        h["anchor_public_upper"] = "2026-10-09T00:00:01Z"
    elif mutation == "missing_kind":
        h["covered_event_kinds"].remove("REMOVAL")
    elif mutation == "raw_mismatch":
        h["events"][0]["sequence"] += 1
    else:
        h["events"].append(deepcopy(h["events"][0]))
        h["events"][-1]["event_id"] = "SECOND_REMOVAL"
        h["declared_event_ids"].append("SECOND_REMOVAL")
        factory.bind_history_sources(request_value)
    result = run(request_value)
    assert expected in codes(result)
    assert_no_quantiles(result)


def test_newer_publication_is_not_same_fact_correction(request_value):
    shares = request_value["records"][0]["classes"][0]["shares"]
    old = shares["assertions"][0]
    set_assertion(request_value, old, "190000000")
    shares["assertions"].append(factory.assertion(request_value, "INDEPENDENT_210M", "210000000",
        coordinate=old["coordinate"], public="2026-10-08T23:00:00Z", publisher="INDEPENDENT_OTHER_PUBLISHER"))
    result = run(request_value)
    assert "CAP_COMPONENT_CONFLICT" in codes(result)
    assert first_cap(result, request_value)["modeled_cap_usd"] is None
    conflict = first_cap(result, request_value)["classes"][0]["shares"]
    assert len(conflict["active_assertion_ids"]) == 2 and len(conflict["active_values"]) == 2
    assert_no_quantiles(result)


def test_same_scope_evidenced_model_correction_retains_both_assertions(request_value):
    shares = request_value["records"][0]["classes"][0]["shares"]
    old = shares["assertions"][0]
    new = factory.assertion(request_value, "REVISED_SHARE_ASSERTION", "1100000", coordinate=old["coordinate"])
    shares["assertions"].append(new)
    shares["relations"] = [factory.relation(request_value, "CORRECTION", old, new)]
    result = run(request_value)
    assert result["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    receipt = first_cap(result, request_value)["classes"][0]["shares"]
    assert receipt["state"] == "MODEL_RESOLVED_SUPERSESSION"
    assert receipt["all_assertion_ids"] == sorted([old["assertion_id"], new["assertion_id"]])
    assert receipt["active_assertion_ids"] == [new["assertion_id"]]
    assert receipt["source_semantics_authenticated"] is False


def test_correction_does_not_remove_independent_competitor(request_value):
    shares = request_value["records"][0]["classes"][0]["shares"]
    old = shares["assertions"][0]
    new = factory.assertion(request_value, "REV", "1100000", coordinate=old["coordinate"])
    other = factory.assertion(request_value, "OTHER", "1200000", coordinate=old["coordinate"], publisher="OTHER")
    shares["assertions"].extend([new, other])
    shares["relations"] = [factory.relation(request_value, "CORRECTION", old, new)]
    result = run(request_value)
    assert "CAP_COMPONENT_CONFLICT" in codes(result)
    receipt = first_cap(result, request_value)["classes"][0]["shares"]
    assert receipt["active_assertion_ids"] == ["OTHER", "REV"]


@cases("mutation,expected", [("cycle", "CYCLIC_SUPERSESSION"), ("scope", "RELATION_SCOPE_MISMATCH"),
    ("cross_publisher", "CROSS_PUBLISHER_RESOLUTION_NOT_IMPLEMENTED"), ("missing", "RELATION_ID_OR_REFERENCE_INVALID")])
def test_invalid_relation_graphs_refuse_instead_of_selecting_a_value(request_value, mutation, expected):
    bundle = request_value["records"][0]["classes"][0]["shares"]
    old = bundle["assertions"][0]
    new = factory.assertion(request_value, "REV", "1100000", coordinate=old["coordinate"])
    bundle["assertions"].append(new)
    bundle["relations"] = [factory.relation(request_value, "R1", old, new)]
    if mutation == "cycle":
        bundle["relations"].append(factory.relation(request_value, "R2", new, old))
    elif mutation == "scope":
        bundle["relations"][0]["fact_coordinate"] = "2026-09-16"
    elif mutation == "cross_publisher":
        new["publisher_id"] = "INDEPENDENT"
    else:
        bundle["relations"][0]["old_id"] = "MISSING"
    result = run(request_value)
    assert expected in codes(result)
    assert_no_quantiles(result)


def test_post_k_assertion_and_post_k_correction_cannot_leak(request_value):
    bundle = request_value["records"][0]["classes"][0]["shares"]
    old = bundle["assertions"][0]
    post = factory.assertion(request_value, "POST_K", "200000000", coordinate=old["coordinate"], public="2026-10-09T00:00:01Z")
    bundle["assertions"].append(post)
    bundle["relations"] = [factory.relation(request_value, "POST_K_CORRECTION", old, post, public="2026-10-10T00:00:00Z")]
    result = run(request_value)
    assert result["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    receipt = first_cap(result, request_value)["classes"][0]["shares"]
    assert receipt["active_assertion_ids"] == [old["assertion_id"]]
    assert {r["reason"] for r in receipt["exclusions"]} == {"POST_CUTOFF_SOURCE"}


def test_latest_measurement_wins_over_publication_recency_and_retains_older_conflict(request_value):
    bundle = request_value["records"][0]["classes"][0]["shares"]
    old = bundle["assertions"][0]
    old["public_upper"] = "2026-10-08T00:00:00Z"
    other = factory.assertion(request_value, "OLDER_CONFLICT", "2000000", coordinate=old["coordinate"])
    latest = factory.assertion(request_value, "LATEST_MEASUREMENT", "3000000", coordinate="2026-09-20")
    bundle["assertions"].extend([other, latest])
    result = run(request_value)
    assert result["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    receipt = first_cap(result, request_value)["classes"][0]["shares"]
    assert receipt["selected_coordinate"] == "2026-09-20"
    assert receipt["active_assertion_ids"] == ["LATEST_MEASUREMENT"]
    assert len(receipt["older_conflicts_retained"]) == 1
    duplicate = factory.assertion(request_value, "LATEST_CONFLICT", "4000000", coordinate="2026-09-20")
    bundle["assertions"].append(duplicate)
    failed = run(request_value)
    assert "CAP_COMPONENT_CONFLICT" in codes(failed)
    assert_no_quantiles(failed)


def test_retraction_without_replacement_is_unavailable(request_value):
    bundle = request_value["records"][0]["classes"][0]["shares"]
    old = bundle["assertions"][0]
    bundle["relations"] = [factory.relation(request_value, "RETRACT", old, kind="RETRACTS")]
    result = run(request_value)
    assert "CAP_COMPONENT_UNAVAILABLE" in codes(result)
    assert first_cap(result, request_value)["modeled_cap_usd"] is None


def test_equivalent_mirrors_are_retained_not_independent_votes(request_value):
    bundle = request_value["records"][0]["classes"][0]["shares"]
    old = bundle["assertions"][0]
    mirror = factory.assertion(request_value, "MIRROR", "1000000.0", coordinate=old["coordinate"], publisher="MIRROR_PUBLISHER")
    bundle["assertions"].append(mirror)
    bundle["relations"] = [factory.relation(request_value, "ALIAS_LINK", old, mirror, kind="ALIAS")]
    result = run(request_value)
    receipt = first_cap(result, request_value)["classes"][0]["shares"]
    assert receipt["state"] == "MODEL_RESOLVED_EQUIVALENT"
    assert len(receipt["active_assertion_ids"]) == 2
    assert receipt["independent_evidence_count"] is None


def test_persistent_overlapping_states_conflict_despite_later_start():
    request = {"sources": []}
    first = factory.assertion(request, "FIRST", "1", coordinate="2026-01-01")
    later = factory.assertion(request, "LATER", "2", coordinate="2026-09-01")
    bundle = {"state_kind": "PERSISTENT", "assertions": [first, later], "relations": []}
    value, _, _, receipt = kernel.resolve_assertions(bundle, kernel._Context(request["sources"]),
        issuer_id="MODEL_ISSUER", class_id="PAIR", component="RATIO")
    assert value is None and receipt["state"] == "CAP_COMPONENT_CONFLICT"
    bundle["relations"] = [factory.relation(request, "CLAIMED_TRANSITION", first, later)]
    with assert_raises(kernel.ContractError, "PERSISTENT_TRANSITION_NOT_IMPLEMENTED"):
        kernel.resolve_assertions(bundle, kernel._Context(request["sources"]), issuer_id="MODEL_ISSUER", class_id="PAIR", component="RATIO")


def signed_retirement(request, value="-10000000", zero=False):
    cls = request["records"][0]["classes"][0]
    set_assertion(request, cls["shares"]["assertions"][0], "100000000", coordinate="2026-09-01")
    set_assertion(request, cls["price"]["assertions"][0], "20")
    eid = "DISCLOSED_RETIREMENT"
    event = {"event_id": eid, "effective_date": "2026-09-20", "sequence": 1, "kind": "DELTA",
        "public_upper": "2026-10-01T00:00:00Z", "value": value,
        "before_basis": "ORDINARY_D_UNITS", "after_basis": "ORDINARY_D_UNITS",
        "evidence": factory.source(request, value),
        "zero_evidence": factory.source(request, "EXPLICIT_NO_CHANGE:" + eid) if zero else None}
    cls["actions"], cls["declared_event_ids"], cls["share_bridge_event_ids"] = [event], [eid], [eid]
    return cls


def test_signed_retirement_preserved_and_crosses_absolute_boundary_correctly(request_value):
    signed_retirement(request_value)
    result = run(request_value)
    receipt = first_cap(result, request_value)
    assert rational_value(receipt["modeled_cap_usd"]) == 1800000000
    assert kernel.absolute_band(rational_value(receipt["modeled_cap_usd"])) == "S_ABS"
    assert kernel.absolute_band(Fraction(2200000000)) == "M_ABS"  # abs(delta) would be wrong.


def test_zero_delta_requires_separate_explicit_no_change_span(request_value):
    signed_retirement(request_value, "0")
    result = run(request_value)
    assert "ZERO_DELTA_EVIDENCE_REQUIRED" in codes(result)
    assert_no_quantiles(result)
    signed_retirement(request_value, "0", zero=True)
    passed = run(request_value)
    assert rational_value(first_cap(passed, request_value)["modeled_cap_usd"]) == 2000000000


def test_retirement_cannot_make_class_nonpositive_or_be_omitted(request_value):
    signed_retirement(request_value, "-100000000")
    result = run(request_value)
    assert "NONPOSITIVE_RESULTING_CLASS_SHARES" in codes(result)
    assert_no_quantiles(result)


@cases("value", [True, False, 1, 1.0, float("nan"), float("inf"), "NaN", "Infinity", "1e3", "1/2", " 1", ".1", "1."])
def test_numeric_parser_rejects_bool_binary_float_nonfinite_or_unbounded_syntax(value):
    with assert_raises(kernel.ContractError, "DECIMAL_STRING_REQUIRED"):
        kernel.rational(value)


@cases("value", ["0", "-1", "-0.01"])
def test_nonpositive_prices_fx_and_multiplicative_factors_remain_invalid(value):
    with assert_raises(kernel.ContractError, "STRICTLY_POSITIVE_REQUIRED"):
        kernel.rational(value, "positive")
    assert kernel.rational(value, "delta", evidenced_zero=True) == Fraction(value)


def test_boolean_share_value_refuses_at_byte_api(request_value):
    request_value["records"][0]["classes"][0]["shares"]["assertions"][0]["value"] = True
    result = run(request_value)
    assert "DECIMAL_STRING_REQUIRED" in codes(result)
    assert_no_quantiles(result)


@cases("literal", [b"1.0", b"1e3", b"NaN", b"Infinity", b"-Infinity"])
def test_noninteger_json_literals_refuse_before_derivation(literal):
    result = kernel.diagnose(b'{"number":' + literal + b'}', policy_bytes=POLICY, adoption_bytes=ADOPTION)
    assert "NON_INTEGER_JSON_NUMBER" in codes(result)
    assert_real_hold(result)


def split_price_fixture(request):
    cls = request["records"][0]["classes"][0]
    cls["d_basis"] = "AFTER_SPLIT"
    set_assertion(request, cls["shares"]["assertions"][0], "200", coordinate="2026-09-29", unit_basis="AFTER_SPLIT")
    set_assertion(request, cls["price"]["assertions"][0], "20", coordinate="2026-09-25", unit_basis="BEFORE_SPLIT")
    cls["calendar"] = ["2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30"]
    event = {"event_id": "SPLIT_2_FOR_1", "effective_date": "2026-09-28", "sequence": 1, "kind": "SPLIT",
             "public_upper": "2026-10-01T00:00:00Z", "value": "2", "before_basis": "BEFORE_SPLIT",
             "after_basis": "AFTER_SPLIT", "evidence": factory.source(request, "2"), "zero_evidence": None}
    cls["actions"] = [event]
    cls["declared_event_ids"] = ["SPLIT_2_FOR_1"]
    cls["price_bridge_event_ids"] = ["SPLIT_2_FOR_1"]
    return cls


def test_stale_split_price_requires_inverse_bridge_even_when_shares_already_postsplit(request_value):
    cls = split_price_fixture(request_value)
    result = run(request_value)
    cap = first_cap(result, request_value)
    assert rational_value(cap["modeled_cap_usd"]) == 2000
    assert rational_value(cap["classes"][0]["modeled_d_equivalent_price"]) == 10
    cls["price_bridge_event_ids"] = []
    failed = run(request_value)
    assert "EXPLICIT_BRIDGE_EVENT_SET_MISMATCH" in codes(failed)
    assert_no_quantiles(failed)


@cases("mutation,expected", [("missing_numeric", "MATERIAL_ACTION_QUANTITY_UNAVAILABLE"),
    ("nonpositive_factor", "STRICTLY_POSITIVE_REQUIRED"), ("same_day", "SAME_DAY_ACTION_ORDER_UNPROVEN"),
    ("wrong_basis", "STALE_PRICE_SPLIT_BASIS_UNPROVEN"), ("duplicate", "DUPLICATE_ACTION_OR_AMBIGUOUS_ORDER")])
def test_action_dependency_failures_hold_whole_issuer(request_value, mutation, expected):
    cls = split_price_fixture(request_value)
    if mutation == "missing_numeric":
        cls["actions"][0]["value"] = None
    elif mutation == "nonpositive_factor":
        cls["actions"][0]["value"] = "-2"
        cls["actions"][0]["evidence"] = factory.source(request_value, "-2")
    elif mutation == "same_day":
        cls["actions"][0]["effective_date"] = "2026-09-29"
    elif mutation == "wrong_basis":
        cls["actions"][0]["before_basis"] = "UNRELATED_UNITS"
    else:
        cls["actions"].append(deepcopy(cls["actions"][0]))
    result = run(request_value)
    assert expected in codes(result)
    assert first_cap(result, request_value)["modeled_cap_usd"] is None
    assert_no_quantiles(result)


def test_no_partial_cap_for_missing_or_unsupported_positive_class(request_value):
    request_value["records"][0]["class_ids"].append("UNPRICED")
    result = run(request_value)
    assert "ECONOMIC_CLASS_SET_INCOMPLETE_OR_DUPLICATE" in codes(result)
    assert first_cap(result, request_value)["modeled_cap_usd"] is None
    assert_no_quantiles(result)


@cases("kind", ["ADR", "UNLISTED_PROXY", "ZERO_OR_CEASED"])
def test_richer_class_semantics_are_typed_holds_not_fabricated_cap(request_value, kind):
    request_value["records"][0]["classes"][0]["kind"] = kind
    result = run(request_value)
    assert "RICHER_CLASS_RIGHTS_OR_CEASED_FACT_NOT_IMPLEMENTED" in codes(result)
    assert_no_quantiles(result)


def test_fx_uses_exact_common_date_and_currency_per_eur_direction(request_value):
    cls = request_value["records"][0]["classes"][0]
    cls["currency"] = "GBP"
    cls["quote_scale"] = "0.01"
    cls["quote_scale_evidence"] = factory.source(request_value, "0.01")
    request_value["fx"]["rates"].append({"currency": "GBP", "bundle": factory.point_bundle(
        request_value, "GBP_RATE", "0.8", basis="UNITS_GBP_PER_EUR")})
    result = run(request_value)
    assert rational_value(first_cap(result, request_value)["modeled_cap_usd"]) == Fraction(1000000) * 4 / 100 * Fraction(11, 8)
    request_value["fx"]["reference_date"] = "2026-09-29"
    failed = run(request_value)
    assert "FX_COMMON_DATE_UNAVAILABLE" in codes(failed)
    assert_no_quantiles(failed)


def test_fx_same_pair_conflict_is_retained_and_never_chooses_newer_publication(request_value):
    usd = request_value["fx"]["rates"][0]["bundle"]
    usd["assertions"].append(factory.assertion(request_value, "OTHER_FX", "1.2", basis="UNITS_USD_PER_EUR", publisher="MIRROR_OR_OTHER"))
    result = run(request_value)
    assert "CAP_COMPONENT_CONFLICT" in codes(result)
    assert result["synthetic"]["modeled_fx"]["assertions"][0]["modeled_value"] is None
    assert len(result["synthetic"]["modeled_fx"]["assertions"][0]["active_assertion_ids"]) == 2
    assert_no_quantiles(result)


@cases("value,state", [(None, "UNKNOWN"), (True, "INVALID_COUNT"), (-1, "INVALID_COUNT"), ("0", "INVALID_COUNT")])
def test_unknown_invalid_counts_are_not_zero(request_value, value, state):
    request_value["counts"]["potentially_eligible_omission_count"] = value
    result = run(request_value)
    assert result["supplied_counts"]["potentially_eligible_omission_count"]["state"] == state
    assert result["supplied_counts"]["potentially_eligible_omission_count"]["supplied_value"] is None
    assert_no_quantiles(result)


def test_missing_count_and_not_published_are_distinct_from_provided_zero(request_value):
    del request_value["counts"]["potentially_eligible_omission_count"]
    result = run(request_value)
    assert result["supplied_counts"]["potentially_eligible_omission_count"]["state"] == "MISSING"
    request_value["counts"]["potentially_eligible_omission_count"] = 0
    request_value["counts"]["source_declared_total"] = "NOT_PUBLISHED"
    result = run(request_value)
    assert result["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    assert result["supplied_counts"]["source_declared_total"]["state"] == "NOT_PUBLISHED"
    assert result["supplied_counts"]["potentially_eligible_omission_count"]["supplied_value"] == 0


def test_real_mode_is_unconditionally_held_even_with_coherent_fixture_and_claims(request_value):
    request_value.pop("mode")
    request_value["claims"] = {"producer_success": True, "source_authority_verified": True, "history_proven": True,
                               "rights_verified": True, "receipt_sha256": "f" * 64, "owner_id": "CEO",
                               "source_path": "authenticated-looking/path", "actual_F": "2026-10-09T13:00:00Z"}
    result = run(request_value)
    assert_real_hold(result)
    assert result["request_mode"] == "REAL_SOURCE" and result["model_state"] == "NOT_RUN"
    assert result["synthetic"] is None
    assert result["supplied_record_checks"]["input_record_count"] == 168
    request_value["mode"] = "REAL_SOURCE"
    assert run(request_value)["synthetic"] is None


def test_claiming_synthetic_does_not_authenticate_real_looking_ids(request_value):
    r = request_value["records"][0]
    r["issuer_id"] = "REAL_LOOKING_COMPANY_NAME"
    result = run(request_value)
    assert_real_hold(result)
    assert result["synthetic"]["real_identity_history_rights_and_evidence_authentication"] is False
    assert result["synthetic"]["genuine_case_requirement_satisfied"] is False


def test_independent_source_axes_do_not_conflate_hash_match_with_authority(request_value):
    result = run(request_value)
    assert result["axes"]["retained_byte_integrity_state"] == "SUPPLIED_BYTES_MATCH_SELF_DECLARED_BINDINGS"
    assert_real_hold(result)
    request_value["sources"][0]["content"] += "tamper"
    corrupt = run(request_value)
    assert "SUPPLIED_BYTE_BINDING_MISMATCH" in codes(corrupt)
    assert corrupt["axes"]["retained_byte_integrity_state"] == "SUPPLIED_BYTE_BINDING_MISMATCH"
    assert_no_quantiles(corrupt)


def test_byte_span_uses_utf8_offsets_not_character_positions(request_value):
    a = request_value["records"][0]["classes"][0]["price"]["assertions"][0]
    evidence = factory.source(request_value, "💡4")
    a["evidence"] = dict(evidence, start=1, end=2)
    failed = run(request_value)
    assert "SOURCE_SPAN_VALUE_MISMATCH" in codes(failed)
    a["evidence"] = dict(evidence, start=4, end=5)
    assert run(request_value)["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"


def test_global_assertion_id_reuse_cannot_bind_two_facts(request_value):
    source = request_value["records"][0]["classes"][0]["shares"]["assertions"][0]
    request_value["records"][1]["classes"][0]["shares"]["assertions"][0]["assertion_id"] = source["assertion_id"]
    result = run(request_value)
    assert "ASSERTION_ID_REUSED_ACROSS_COMPONENTS" in codes(result)
    assert_no_quantiles(result)


def test_closed_objects_duplicate_json_keys_and_real_adapter_claims_refuse(request_value):
    request_value["real_source_adapter"] = "successful_adapter"
    result = run(request_value)
    assert "CLOSED_OBJECT_SHAPE" in codes(result)
    duplicate = kernel.diagnose(b'{"schema":"a","schema":"b"}', policy_bytes=POLICY, adoption_bytes=ADOPTION)
    assert "DUPLICATE_JSON_KEY" in codes(duplicate)
    request_value.pop("real_source_adapter")
    request_value["records"][0]["classes"][0]["shares"]["assertions"][0]["verified"] = True
    nested = run(request_value)
    assert "CLOSED_OBJECT_SHAPE" in codes(nested)
    assert_no_quantiles(nested)


def test_explicit_input_depth_source_record_and_output_budgets(request_value):
    result = kernel.diagnose(b" " * (2 * 1024 * 1024 + 1), policy_bytes=POLICY, adoption_bytes=ADOPTION)
    assert "INPUT_BYTE_LIMIT" in codes(result)
    nested = kernel.diagnose(b"[" * 25 + b"0" + b"]" * 25, policy_bytes=POLICY, adoption_bytes=ADOPTION)
    assert "JSON_DEPTH_LIMIT" in codes(nested)
    large = "x" * (256 * 1024 + 1)
    factory.source(request_value, large)
    result = run(request_value)
    assert "SOURCE_BYTE_LIMIT" in codes(result)
    too_many = factory.make_request()
    too_many["records"] = [deepcopy(too_many["records"][0]) for _ in range(513)]
    assert "ARRAY_SHAPE_OR_LIMIT" in codes(run(too_many))
    hypothetical = kernel._base_result()
    hypothetical["synthetic"] = {"oversized": "x" * (8 * 1024 * 1024)}
    refused = kernel._finish(hypothetical)
    assert "OUTPUT_BYTE_LIMIT" in codes(refused)
    assert refused["synthetic"] is None and refused["model_state"] == "OUTPUT_REFUSED"
    assert_real_hold(refused)


def test_supplied_stress_cases_cannot_satisfy_genuine_cases_or_replace_issuers(request_value):
    baseline = run(request_value)
    selected = baseline["synthetic"]["selection"]["selected_issuer_ids"]
    lookup = {r["issuer_id"]: r for r in baseline["synthetic"]["modeled_candidates"]}
    by_stratum = {}
    for issuer in selected:
        country = lookup[issuer]["country"]
        by_stratum.setdefault(country if country in ("US", "CN_MAINLAND", "HK", "CA") else "INT", issuer)
    for stratum, issuer in by_stratum.items():
        for i in range(6):
            request_value["stress_cases"].append({"case_id": stratum + str(i), "stratum": stratum, "issuer_id": issuer,
                "document_id": "ARTIFICIAL_DOC_2025", "document_role": "ANNUAL_2025", "locator": str(i),
                "label": "DUAL_FLOW", "evidence": factory.source(request_value, "DUAL_FLOW"),
                "independent_review_id": "UNTRUSTED_REVIEWER", "before_vendor_outputs": True})
    result = run(request_value)
    assert result["synthetic"]["selection"]["selected_issuer_ids"] == selected
    assert result["stress_cases"]["supplied_case_count"] == 30
    assert set(result["stress_cases"]["modeled_shortfall_per_stratum"].values()) == {0}
    assert result["stress_cases"]["actual_genuine_case_count"] is None
    assert result["stress_cases"]["genuine_case_requirement"].startswith("NOT_ESTABLISHED")
    assert result["stress_cases"]["missing_cases_replace_issuers"] is False


def test_cli_regular_file_read_outputs_explicit_not_ready_and_matches_api(tmp_path):
    request_path = tmp_path / "artificial.json"
    request_path.write_bytes(factory.encode(factory.make_request()))
    policy_path, adoption_path = tmp_path / "policy.json", tmp_path / "adoption.json"
    policy_path.write_bytes(POLICY)
    adoption_path.write_bytes(ADOPTION)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, "-B", str(KERNEL_DIR / "source_diagnostic.py"), "--input", str(request_path),
               "--policy", str(policy_path), "--adoption", str(adoption_path)]
    proc = subprocess.run(command, capture_output=True, env=env, check=False, timeout=15)
    assert proc.returncode == 2 and proc.stderr == b""
    result = json.loads(proc.stdout)
    assert result["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    assert_real_hold(result)
    assert proc.stdout == kernel.canonical_bytes(run(factory.make_request())) + b"\n"
    link = tmp_path / "symlink.json"
    link.symlink_to(request_path)
    command[command.index("--input") + 1] = str(link)
    refused = subprocess.run(command, capture_output=True, env=env, check=False, timeout=15)
    assert refused.returncode == 2
    assert "CLI_INPUT_UNAVAILABLE_OR_REFUSED" in codes(json.loads(refused.stdout))


def test_derived_rational_bit_budget_is_exact_and_explicit():
    accepted = kernel._rational_json(Fraction((1 << 8192) - 1))
    assert int(accepted["numerator"]) == (1 << 8192) - 1
    with assert_raises(kernel.ContractError, "EXACT_ARITHMETIC_BUDGET"):
        kernel._rational_json(Fraction(1 << 8192))
    with assert_raises(kernel.ContractError, "EXACT_ARITHMETIC_BUDGET"):
        kernel._rational_json(Fraction(1, (1 << 8192) + 1))


def test_share_measurement_age_boundary_and_typed_older_refusal(request_value):
    from datetime import timedelta
    shares = request_value["records"][0]["classes"][0]["shares"]["assertions"][0]
    shares["coordinate"] = (kernel.D - timedelta(days=183)).isoformat()
    assert run(request_value)["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    shares["coordinate"] = (kernel.D - timedelta(days=184)).isoformat()
    result = run(request_value)
    assert "CAP_COMPONENT_UNAVAILABLE" in codes(result)
    receipt = first_cap(result, request_value)["classes"][0]["shares"]
    assert receipt["exclusions"][0]["reason"] == "COMPONENT_TOO_OLD"
    assert_no_quantiles(result)


def test_price_requires_both_calendar_day_and_session_age_limits(request_value):
    cls = request_value["records"][0]["classes"][0]
    price = cls["price"]["assertions"][0]
    price["coordinate"] = "2026-09-20"
    cls["calendar"] = ["2026-09-20", "2026-09-23", "2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29"]
    assert run(request_value)["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    cls["calendar"].append("2026-09-30")
    assert "PRICE_TOO_OLD" in codes(run(request_value))
    price["coordinate"] = "2026-09-19"
    result = run(request_value)
    assert "CAP_COMPONENT_UNAVAILABLE" in codes(result)
    assert_no_quantiles(result)


def test_supplied_assertion_clocks_and_spans_survive_resolution(request_value):
    result = run(request_value)
    supplied = request_value["records"][0]["classes"][0]["shares"]
    receipt = first_cap(result, request_value)["classes"][0]["shares"]
    assert receipt["supplied_assertions"] == supplied["assertions"]
    raw = factory.encode(supplied)
    assert receipt["bundle_content_binding"] == {"byte_length": len(raw), "sha256": sha256(raw).hexdigest()}


@cases("timestamp,expected", [
    ("2026-10-09T00:00:00Z", None),
    ("2026-10-09T00:00:00.0Z", None),
    ("2026-10-09T00:00:00.000000Z", None),
    ("2026-10-08T23:59:59.999999Z", None),
    ("2026-10-09T00:00:00.000001Z", "POST_CUTOFF_ANCHOR"),
    ("2026-10-09T00:00:00.0000001Z", "UTC_TIMESTAMP_PRECISION_UNSUPPORTED"),
    ("2026-10-09T00:00:00.0000000Z", "UTC_TIMESTAMP_PRECISION_UNSUPPORTED"),
    ("2026-10-08T23:59:59.9999999Z", "UTC_TIMESTAMP_PRECISION_UNSUPPORTED"),
    ("2026-10-09T00:00:00,000000Z", "EXPLICIT_UTC_BOUND_REQUIRED"),
    ("2026-10-09T00:00:00+00:00", "EXPLICIT_UTC_BOUND_REQUIRED"),
    ("20261009T00:00:00Z", "EXPLICIT_UTC_BOUND_REQUIRED"),
    ("2026-W41-5T00:00:00Z", "EXPLICIT_UTC_BOUND_REQUIRED"),
    ("2026-02-30T00:00:00Z", "EXPLICIT_UTC_BOUND_REQUIRED"),
    ("2026-10-09T00:00Z", "EXPLICIT_UTC_BOUND_REQUIRED"),
    ("2026-10-09T00:00:00Z\n", "EXPLICIT_UTC_BOUND_REQUIRED"),
    ("2026-10-09T00:00:00.٠Z", "EXPLICIT_UTC_BOUND_REQUIRED"),
])
def test_public_anchor_has_exact_declared_utc_precision(request_value, timestamp, expected):
    request_value["history"]["anchor_public_upper"] = timestamp
    result = run(request_value)
    assert_real_hold(result)
    if expected is None:
        assert result["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
        assert len(result["synthetic"]["selection"]["selected_issuer_ids"]) == 120
    else:
        assert expected in codes(result)
        assert_no_quantiles(result)


@cases("consumer", ["membership_event", "share_assertion", "price_assertion",
                    "fx_assertion", "relation", "action"])
def test_public_timestamp_consumers_never_truncate_finer_precision(request_value, consumer):
    if consumer == "membership_event":
        removal_reconstruction(request_value)
        row = request_value["history"]["events"][0]
    elif consumer == "relation":
        bundle = request_value["records"][0]["classes"][0]["shares"]
        old = bundle["assertions"][0]
        new = factory.assertion(request_value, "PRECISION_CORRECTION", "1100000",
                                coordinate=old["coordinate"])
        bundle["assertions"].append(new)
        row = factory.relation(request_value, "PRECISION_RELATION", old, new)
        bundle["relations"] = [row]
    elif consumer == "action":
        row = signed_retirement(request_value)["actions"][0]
    elif consumer == "fx_assertion":
        row = request_value["fx"]["rates"][0]["bundle"]["assertions"][0]
    else:
        key = "shares" if consumer == "share_assertion" else "price"
        row = request_value["records"][0]["classes"][0][key]["assertions"][0]
    row["public_upper"] = "2026-10-09T00:00:00.000000Z"
    if consumer == "membership_event":
        factory.bind_history_sources(request_value)
    valid = run(request_value)
    assert valid["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
    assert_real_hold(valid)
    row["public_upper"] = "2026-10-09T00:00:00.0000001Z"
    if consumer == "membership_event":
        factory.bind_history_sources(request_value)
    refused = run(request_value)
    assert "UTC_TIMESTAMP_PRECISION_UNSUPPORTED" in codes(refused)
    assert_no_quantiles(refused)


@cases("timestamp,expected_cap", [
    ("2026-10-08T23:59:59.999999Z", 2100000000),
    ("2026-10-09T00:00:00Z", 2100000000),
    ("2026-10-09T00:00:00.000000Z", 2100000000),
    ("2026-10-09T00:00:00.000001Z", 1900000000),
    ("2026-10-09T00:00:00.0000001Z", None),
])
def test_public_correction_cannot_cross_k_by_precision_loss(request_value, timestamp, expected_cap):
    cls = request_value["records"][0]["classes"][0]
    old = cls["shares"]["assertions"][0]
    set_assertion(request_value, old, "190000000")
    set_assertion(request_value, cls["price"]["assertions"][0], "10")
    new = factory.assertion(request_value, "CUTOFF_210M_CORRECTION", "210000000",
                            coordinate=old["coordinate"], public=timestamp)
    cls["shares"]["assertions"].append(new)
    cls["shares"]["relations"] = [factory.relation(request_value, "CUTOFF_RELATION",
                                                  old, new, public=timestamp)]
    result = run(request_value)
    assert_real_hold(result)
    if expected_cap is None:
        assert "UTC_TIMESTAMP_PRECISION_UNSUPPORTED" in codes(result)
        assert_no_quantiles(result)
    else:
        assert result["model_state"] == "ARTIFICIAL_MODEL_COMPLETE"
        cap = first_cap(result, request_value)["modeled_cap_usd"]
        assert rational_value(cap) == expected_cap


class TestSourceDiagnosticKernel(unittest.TestCase):
    """Actual standard-library tests, also discoverable by pytest."""


def _install_unittest_cases():
    functions = [(name, value) for name, value in list(globals().items())
                 if name.startswith("test_") and inspect.isfunction(value)]
    for name, function in functions:
        names, values = getattr(function, "_cases", ([], [()]))
        for index, values_for_case in enumerate(values):
            if len(names) == 1:
                values_for_case = (values_for_case,)
            parameters = dict(zip(names, values_for_case))

            def method(self, function=function, parameters=parameters):
                kwargs = dict(parameters)
                arguments = inspect.signature(function).parameters
                if "request_value" in arguments:
                    kwargs["request_value"] = factory.make_request()
                if "tmp_path" in arguments:
                    with tempfile.TemporaryDirectory(prefix="wp02-kernel-",
                            dir=os.environ.get("GMI_KERNEL_TEST_TMPDIR")) as directory:
                        kwargs["tmp_path"] = Path(directory)
                        function(**kwargs)
                else:
                    function(**kwargs)

            test_name = name + ("__case_" + str(index + 1) if names else "")
            method.__name__, method.__doc__ = test_name, function.__doc__
            setattr(TestSourceDiagnosticKernel, test_name, method)
        del globals()[name]


_install_unittest_cases()

if __name__ == "__main__":
    unittest.main(verbosity=2)
