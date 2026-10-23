#!/usr/bin/env python3
"""Independent executable challenge of the fixed intelligence laboratory.

Reads the original lab without mutation or bytecode writes. Replays its original
suite in an owned temporary directory and retains counterexamples here only.
"""
from __future__ import annotations

import ast
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
# Preserve the exact challenged version so a later parent repair does not erase
# the counterexample's reproducibility. These bytes were copied without edits.
LAB = HERE / "reviewed_source"
PINNED = {
    "DESIGN.md": "6432eb2f25be89f6fc77b6410dc398e34abf5263d031f9e4aa460b0639a0cde4",
    "contract_lab.py": "377dde6af13c890d5b694769408ceaea2515e2a0b4018998128eeb86e150d559",
    "source_input.json": "a031323d82e99833ffdd5b35140ee6f686e65ca077a038cfaca57e280de00334",
    "results.json": "8389a41b28453dae511f46607d783b8aa41986e97380adb4e056bee5fcf9c2cb",
    "analyst_duplicates.json": "6f03613836e17e0ec1016d5f244e998b29cc63bd6834dee7bc1f4c1648137c4b",
}
CUTOFF = "2026-10-09T08:00:00Z"
SESSIONS = {"valuation": "2026-10-09", "margin": "2026-10-08"}


def check(value, message):
    if not value:
        raise AssertionError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fact(ticker="600000.SS", value=1.0, **updates):
    row = {"ticker": ticker, "family": "valuation", "observation_key": "2026-10-09",
           "source_record_id": ticker + "/valuation/2026-10-09", "revision": 0,
           "value": value, "source_blob_sha256": "a" * 64,
           "published_at": "2026-10-09T07:00:00Z", "first_seen_at": "2026-10-09T07:01:00Z",
           "effective_from": "2026-10-09T07:00:00Z", "cadence": "session",
           "observation_session": "2026-10-09", "status": "active"}
    row.update(updates)
    return row


def attempt(function):
    try:
        return {"returned": function()}
    except Exception as ex:
        return {"exception": type(ex).__name__, "message": str(ex)}


def main():
    blobs = {name: (LAB / name).read_bytes() for name in PINNED}
    for name, value in blobs.items():
        check(sha(value) == PINNED[name], "Reviewed lab changed: " + name)
    source_text = blobs["contract_lab.py"].decode()
    inp = json.loads(blobs["source_input.json"])
    original = json.loads(blobs["results.json"])
    namespace = {"__name__": "reviewed_contract_lab", "__file__": str(LAB / "contract_lab.py")}
    exec(compile(source_text, str(LAB / "contract_lab.py"), "exec"), namespace)
    snapshot = namespace["source_snapshot"]
    order = namespace["qualified_order"]
    with tempfile.TemporaryDirectory(prefix="original_suite_", dir=HERE) as temporary:
        folder = Path(temporary)
        (folder / "contract_lab.py").write_bytes(blobs["contract_lab.py"])
        (folder / "source_input.json").write_bytes(blobs["source_input.json"])
        replay = {"__name__": "review_original_suite", "__file__": str(folder / "contract_lab.py")}
        exec(compile(source_text, str(folder / "contract_lab.py"), "exec"), replay)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            replay["main"]()
        replay_bytes = (folder / "results.json").read_bytes()
        check(replay_bytes == blobs["results.json"], "Original 56-check output does not reproduce byte-for-byte")
    source_functions = namespace["load_source_functions"](inp)
    # Execute the lab's actual nested normalization helper without modifying it.
    tree = ast.parse(source_text)
    main_node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    normal_node = next(node for node in main_node.body if isinstance(node, ast.FunctionDef) and node.name == "normal")
    normal_scope = {"source": source_functions, "ContractError": namespace["ContractError"]}
    exec(compile(ast.Module(body=[deepcopy(normal_node)], type_ignores=[]), "lab_normal_as_written", "exec"), normal_scope)
    normal = normal_scope["normal"]
    tests = []

    def record(name, category, expected, observed, holds, severity="control"):
        tests.append({"name": name, "category": category, "severity": severity,
                      "expected_invariant": expected, "observed": observed, "invariant_holds": bool(holds)})

    a, b = fact(), fact("000001.SZ", 3.0)
    base = snapshot([a, b], CUTOFF, expected_sessions=SESSIONS)
    record("current_population_reproduction", "control", "Existing numerical controls reproduce without claiming actual source-time coverage",
           {"original_check_n": original["check_count"], "byte_identical_replay": True,
            "qualified_n": original["current_qualified_intelligence"]["qualified_n"],
            "featured_overlap": len(set(original["current_v3_control"]["selected"]) & set(original["current_qualified_intelligence"]["selected"]))},
           original["check_count"] == 56)
    future = fact("600111.SS", True, first_seen_at="2026-10-09T09:00:00Z", published_at="2026-10-09T08:30:00Z")
    out = snapshot([a, b, future], CUTOFF, expected_sessions=SESSIONS)
    record("valid_identity_future_invalid_payload_is_ignored", "control", "A later invalid payload cannot alter earlier selected values", out,
           out["selected_input_digest"] == base["selected_input_digest"])
    retracted = dict(a, revision=1, status="retracted", value=None)
    out = snapshot([a, retracted], CUTOFF, expected_sessions=SESSIONS)
    record("known_well_formed_retraction_suppresses", "control", "Known validly timestamped retraction suppresses old value", out,
           not out["selected"] and out["suppressed"][0]["reason"] == "source_retracted")
    future_effective = dict(a, revision=1, value=8.0, effective_from="2026-10-10T00:00:00Z")
    out = snapshot([a, future_effective], CUTOFF, expected_sessions=SESSIONS)
    record("legitimate_future_effective_correction_keeps_prior", "control", "A valid future applicability timestamp keeps the prior effective value", out,
           len(out["selected"]) == 1 and out["selected"][0]["revision"] == 0)

    integer, boolean = fact(value=1), fact(value=True)
    forward = attempt(lambda: snapshot([integer, boolean], CUTOFF, expected_sessions=SESSIONS))
    reverse = attempt(lambda: snapshot([boolean, integer], CUTOFF, expected_sessions=SESSIONS))
    record("boolean_numeric_duplicate_order_dependence", "demonstrated_failure",
           "Invalid Boolean and measured numeric value cannot coalesce as an exact duplicate; both orders must fail closed consistently",
           {"numeric_first": forward, "boolean_first": reverse},
           forward == reverse and forward.get("exception") == "ContractError", "P1")
    floating = fact(value=1.0)
    forward = snapshot([integer, floating], CUTOFF, expected_sessions=SESSIONS)
    reverse = snapshot([floating, integer], CUTOFF, expected_sessions=SESSIONS)
    record("equal_numeric_representation_changes_digest_by_order", "demonstrated_failure",
           "Equivalent numeric duplicates either canonicalize to one representation or are refused consistently",
           {"integer_first_digest": forward["selected_input_digest"], "float_first_digest": reverse["selected_input_digest"],
            "integer_first_value": forward["selected"][0]["value"], "float_first_value": reverse["selected"][0]["value"]},
           forward["selected_input_digest"] == reverse["selected_input_digest"], "P1")

    for label, updates in [("revision_type", {"revision": "bad"}), ("missing_ticker", {"ticker": None}),
                           ("empty_source_id", {"source_record_id": ""})]:
        row = dict(future, **updates)
        out = attempt(lambda row=row: snapshot([a, b, row], CUTOFF, expected_sessions=SESSIONS))
        record("future_malformed_" + label, "demonstrated_failure",
               "A record with valid future availability cannot break an earlier replay through identity fields", out,
               out.get("returned", {}).get("selected_input_digest") == base["selected_input_digest"], "P1")

    for label, effective in [("missing", None), ("invalid", "not-a-time"), ("naive", "2026-10-09T07:00:00")]:
        row = dict(retracted, effective_from=effective)
        out = attempt(lambda row=row: snapshot([a, row], CUTOFF, expected_sessions=SESSIONS))
        selected = out.get("returned", {}).get("selected", [])
        record("known_retraction_" + label + "_applicability_resurrects", "demonstrated_failure",
               "Known observed/published higher retraction with malformed applicability must quarantine the observation or fail, not return its old active value", out,
               bool(out.get("exception")) or not selected, "P1")

    for label, expected in [("missing", None), ("malformed", "not-a-session")]:
        row = dict(a, observation_session=expected)
        out = attempt(lambda row=row, expected=expected: snapshot([row], CUTOFF, expected_sessions={"valuation": expected}))
        record("invalid_expected_and_observed_session_" + label, "demonstrated_failure",
               "A session contract needs real nonempty session identities; equality of invalid values is insufficient", out,
               bool(out.get("exception")) or not out.get("returned", {}).get("selected"), "P1")
    periodic_override = dict(a, observation_session="2026-01-02", cadence="periodic")
    out = snapshot([periodic_override], CUTOFF, expected_sessions=SESSIONS)
    record("row_cadence_can_bypass_family_session_contract", "unimplemented_contract_boundary",
           "A source family declared session-based by its owner cannot reclassify itself as periodic in a row",
           {"owner_contract_under_test": {"family": "valuation", "cadence": "session", "expected_session": "2026-10-09"},
            "actual_api_accepts_only_expected_sessions": True, "snapshot": out},
           not out["selected"], "P1_before_integration")

    spaced = dict(a, ticker="600000.SS ")
    alias_snapshot = snapshot([a, b, spaced], CUTOFF, expected_sessions=SESSIONS)
    baseline_normal, alias_normal = normal(base), normal(alias_snapshot)
    record("whitespace_issuer_alias_changes_normalization", "demonstrated_failure",
           "An invalid issuer alias cannot create an extra normalization observation for the same source fact",
           {"selected_tickers": [r["ticker"] for r in alias_snapshot["selected"]], "base_percentiles": baseline_normal,
            "alias_percentiles": alias_normal}, baseline_normal == alias_normal, "P1")

    candidate_rows = [dict(r, qualified=True) for r in inp["qualified_rows"]]
    huge_rows = deepcopy(candidate_rows)
    huge_rows[0]["intel"] = 10 ** 400
    out = attempt(lambda: order(huge_rows))
    record("large_json_integer_breaks_atomic_fallback", "demonstrated_failure",
           "Unrepresentable bounded intelligence must trigger a defined atomic fallback, not an uncaught exception", out,
           out.get("returned", {}).get("mode") == "v3_atomic_fallback", "P1")
    out = attempt(lambda: snapshot([a, dict(a, revision=1, value=10 ** 400)], CUTOFF, expected_sessions=SESSIONS))
    record("large_json_integer_breaks_known_revision_suppression", "demonstrated_failure",
           "An unrepresentable latest value produces explicit suppression/refusal within the contract exception model", out,
           out.get("exception") == "ContractError" or ("returned" in out and not out["returned"]["selected"]), "P1")

    margin = fact("000001.SZ", 1000000.0, family="margin", observation_session="2026-10-08", unit="CNY")
    valuation = dict(a, unit="percentile")
    mixed = snapshot([valuation, margin], CUTOFF, expected_sessions=SESSIONS)
    out = attempt(lambda: normal(mixed))
    record("normalization_accepts_incompatible_feed_families", "unimplemented_contract_boundary",
           "The normalization demonstration must refuse mixed feed/measure populations or separate them explicitly",
           {"source_families": [r["family"] for r in mixed["selected"]], "units": [r.get("unit") for r in mixed["selected"]], "normalization": out},
           out.get("exception") == "ContractError", "P1_before_integration")
    contradictory = [dict(ticker="600000.SS", qualified=True, score=10, score_rank=1, intel=0, intel_basis="measured", sector="A"),
                     dict(ticker="000001.SZ", qualified=True, score=90, score_rank=2, intel=0, intel_basis="measured", sector="B")]
    all_zero = order(contradictory)
    fallback_rows = deepcopy(contradictory)
    fallback_rows[0]["intel_basis"] = "missing"
    fallback = order(fallback_rows)
    record("contradictory_incumbent_rank_is_a_caller_premise", "unimplemented_contract_boundary",
           "A valid caller must bind score/rank and intelligence fields to compatible generation/ordering contracts",
           {"all_zero_order": all_zero["ordered"], "fallback_order": fallback["ordered"],
            "current_dataset_has_no_such_contradiction": True}, all_zero["ordered"] == fallback["ordered"], "P2_document_premise")
    mixed_generations = deepcopy(candidate_rows)
    for i, row in enumerate(mixed_generations):
        row["intelligence_generation"] = "unrelated_A" if i % 2 else "unrelated_B"
    out = order(mixed_generations)
    record("numeric_coverage_does_not_certify_generation_compatibility", "unimplemented_contract_boundary",
           "The numeric order prototype cannot establish source-time or generation compatibility without an integration contract",
           {"mode": out["mode"], "qualified_n": out["qualified_n"], "two_generation_labels_ignored": True},
           False, "P2_document_premise")

    duplicates = json.loads(blobs["analyst_duplicates.json"])
    canonical_groups = []
    for group in duplicates["duplicates"]:
        values = {json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) for value in group["payloads"]}
        canonical_groups.append(len(values))
    check(len(canonical_groups) == 475 and set(canonical_groups) == {1}, "Actual analyst duplicate payloads conflict")
    actual_duplicate_control = {"duplicate_groups": len(canonical_groups), "every_group_canonical_payload_identical": True,
                                "rows": duplicates["rows"], "unique_tickers": duplicates["unique_tickers"],
                                "group_sizes": duplicates["group_sizes"], "conflicting_groups": duplicates["conflicting_payload_groups"],
                                "changed_consensus": duplicates["changed_consensus_blocks"], "changed_rating_scores": duplicates["changed_raw_rating_scores"],
                                "changed_percentiles": duplicates["changed_rank_percentiles"],
                                "evidence_limit": "Payload equality and census are independently checked. Full source-reader reversal result is accepted from the hash-bound parent receipt; this challenge does not claim a new remote replay."}
    record("actual_analyst_duplicates_remain_negative_finding", "control", "Do not infer corruption from exact duplicates", actual_duplicate_control,
           duplicates["conflicting_payload_groups"] == duplicates["changed_consensus_blocks"] == duplicates["changed_raw_rating_scores"] == duplicates["changed_rank_percentiles"] == 0)
    for name in PINNED:
        check(sha((LAB / name).read_bytes()) == PINNED[name], "Original lab changed during read-only review")
    failures = [r for r in tests if r["category"] == "demonstrated_failure" and not r["invariant_holds"]]
    boundaries = [r for r in tests if r["category"] == "unimplemented_contract_boundary"]
    result = {"status": "AMEND_BEFORE_IMPLEMENTATION_HANDOFF", "source_sha": inp["source_sha"],
              "reviewed_files_sha256": PINNED, "challenge_script_sha256": sha(Path(__file__).read_bytes()),
              "original_suite": {"check_n": 56, "byte_identical_result": True, "result_sha256": sha(replay_bytes), "stdout": stdout.getvalue().strip()},
              "challenge_case_n": len(tests), "demonstrated_failed_case_n": len(failures),
              "unimplemented_boundary_case_n": len(boundaries), "tests": tests,
              "actual_duplicate_control": actual_duplicate_control,
              "custody": {"reviewed_input_files_unchanged": True, "original_lab_mutations": 0,
                          "original_input_location": "deepening_20261009/intelligence_lab",
                          "writes_confined_to_review_directory": True, "vendor_calls": 0, "production_effects": 0},
              "limits": ["Synthetic counterexamples establish prototype contract gaps, not observed current-data corruption.",
                         "Numerical qualified-population coverage remains separate from temporal/generation-qualified production coverage.",
                         "This review neither installs a feature store nor authorizes intelligence activation."]}
    (HERE / "CHALLENGE_RESULTS.json").write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "challenge_case_n", "demonstrated_failed_case_n", "unimplemented_boundary_case_n"]}))
    print(json.dumps({"failed_cases": [r["name"] for r in failures]}, indent=2))


if __name__ == "__main__":
    main()
