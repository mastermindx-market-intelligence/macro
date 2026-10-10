#!/usr/bin/env python3
"""Independent regression/adversarial acceptance of one repaired research hash.

No production imports or principal writes. Initial review stays immutable.
"""
from __future__ import annotations

import ast
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import itertools
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LAB = HERE / "reviewed_source"
INITIAL = HERE.parent
CUTOFF = "2026-10-09T08:00:00Z"
SESSIONS = {"valuation": "2026-10-09", "margin": "2026-10-08"}
SOURCE_PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def attempt(fun):
    try:
        return {"returned": fun()}
    except Exception as ex:
        return {"exception": type(ex).__name__, "message": str(ex)}


def refused(result, reason=None):
    return result.get("exception") == "ContractError" and (reason is None or result.get("message") == reason)


def fact(ticker="600000.SS", value=1.0, **updates):
    row = {"ticker": ticker, "family": "valuation", "observation_key": "2026-10-09",
           "source_record_id": ticker + "/valuation/2026-10-09", "revision": 0,
           "value": value, "source_blob_sha256": "a" * 64,
           "published_at": "2026-10-09T07:00:00Z", "first_seen_at": "2026-10-09T07:01:00Z",
           "effective_from": "2026-10-09T07:00:00Z", "cadence": "session",
           "observation_session": "2026-10-09", "status": "active", "unit": "synthetic_score"}
    row.update(updates)
    row.setdefault("feature_contract_id", row["family"] + "/synthetic-value/v1")
    return row


def main():
    freeze_bytes = (HERE / "INPUT_FREEZE.json").read_bytes()
    freeze = json.loads(freeze_bytes)
    pins = freeze["repaired_files_sha256"]
    blobs = {name: (LAB / name).read_bytes() for name in pins}
    for name, value in blobs.items():
        check(sha(value) == pins[name], "Repaired snapshot changed: " + name)
    original_hashes = {**freeze["initial_review_payload_sha256"], "MANIFEST.json": freeze["initial_review_manifest_sha256"]}
    for name, expected in original_hashes.items():
        check(sha((INITIAL / name).read_bytes()) == expected, "Initial review changed: " + name)
    prior_acceptance = INITIAL / freeze["prior_repaired_acceptance_directory"]
    prior_hashes = freeze["prior_repaired_acceptance_files_sha256"]
    for name, expected in prior_hashes.items():
        check(sha((prior_acceptance / name).read_bytes()) == expected, "Prior repaired acceptance changed: " + name)
    source_text = blobs["contract_lab.py"].decode()
    inp, published = json.loads(blobs["source_input.json"]), json.loads(blobs["results.json"])
    check(inp["source_sha"] == SOURCE_PIN, "Unexpected study source")
    ns = {"__name__": "acceptance_contract_lab", "__file__": str(LAB / "contract_lab.py")}
    exec(compile(source_text, str(LAB / "contract_lab.py"), "exec"), ns)
    snapshot, order = ns["source_snapshot"], ns["qualified_order"]
    source = ns["load_source_functions"](inp)
    node = next(n for n in ast.parse(source_text).body if isinstance(n, ast.FunctionDef) and n.name == "main")
    normal_node = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "normal")
    normal_ns = {"source": source, "ContractError": ns["ContractError"]}
    exec(compile(ast.Module(body=[deepcopy(normal_node)], type_ignores=[]), "repaired_normal_as_written", "exec"), normal_ns)
    normal = normal_ns["normal"]
    with tempfile.TemporaryDirectory(prefix="principal_suite_", dir=HERE) as temporary:
        folder = Path(temporary)
        for name in ["contract_lab.py", "source_input.json"]:
            (folder / name).write_bytes(blobs[name])
        replay = {"__name__": "acceptance_principal_suite", "__file__": str(folder / "contract_lab.py")}
        exec(compile(source_text, str(folder / "contract_lab.py"), "exec"), replay)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            replay["main"]()
        replay_bytes = (folder / "results.json").read_bytes()
        check(replay_bytes == blobs["results.json"], "Repaired principal result does not reproduce byte-for-byte")
    tests = []

    def record(name, family, expected, observed, holds, original_case=None, disposition="acceptance_gate"):
        tests.append({"name": name, "family": family, "expected_invariant": expected,
                      "observed": observed, "passed": bool(holds), "original_case": original_case,
                      "disposition": disposition})

    def snap(rows, **kw):
        return snapshot(rows, CUTOFF, expected_sessions=SESSIONS, **kw)

    a, b = fact(), fact("000001.SZ", 3.0)
    base = snap([a, b])
    original_receipt = json.loads((INITIAL / "reviewed_source/results.json").read_text())
    check_names = [r["name"] for r in published["checks"]]
    record("principal_56_controls_reproduce", "positive_control",
           "All original check identities remain passing and the repaired result reproduces byte-for-byte",
           {"check_n": published["check_count"], "byte_identical_replay": True,
            "result_sha256": sha(replay_bytes), "same_56_check_names": check_names == [r["name"] for r in original_receipt["checks"]]},
           published["check_count"] == 56 and all(r["passed"] for r in published["checks"]) and check_names == [r["name"] for r in original_receipt["checks"]])
    candidates = [dict(r, qualified=True) for r in inp["qualified_rows"]]
    incumbent = [r["ticker"] for r in sorted(candidates, key=lambda r: (r["score_rank"], r["ticker"]))]
    score_order = [r["ticker"] for r in sorted(candidates, key=lambda r: (-r["score"], r["ticker"]))]
    zeros = order([dict(r, intel=0) for r in candidates])
    fallback_rows = deepcopy(candidates); fallback_rows[0]["intel_basis"] = "missing"
    fallback = order(fallback_rows)
    record("current_population_and_coherent_score_rank", "positive_control",
           "The current 125-name population has coherent score/rank order; all-zero measured intelligence reproduces the actual V3 selection",
           {"qualified_n": len(candidates), "score_rank_coherent": incumbent == score_order,
            "v3_exact_featured": fallback["selected"] == inp["published_featured"],
            "zero_mode": zeros["mode"], "zero_order_equals_v3": zeros["ordered"] == fallback["ordered"],
            "featured_overlap": len(set(order(candidates)["selected"]) & set(fallback["selected"]))},
           len(candidates) == 125 and incumbent == score_order and zeros["ordered"] == fallback["ordered"] and fallback["selected"] == inp["published_featured"])

    for value, floating in [(1, 1.0), (0, 0.0), (-1, -1.0), (2**53, float(2**53))]:
        x, y = fact(value=value), fact(value=floating)
        out = [attempt(lambda rs=rs: snap(rs)) for rs in [[x, y], [y, x]]]
        success = all("returned" in r for r in out)
        holds = success and out[0]["returned"] == out[1]["returned"] and len(out[0]["returned"]["selected"]) == 1 and type(out[0]["returned"]["selected"][0]["value"]) is int
        record("equivalent_numeric_duplicate_" + str(value), "duplicate_identity",
               "Equivalent finite int/float representations coalesce deterministically without losing integer identity", out, holds,
               "equal_numeric_representation_changes_digest_by_order" if value == 1 else None)
    for numeric, boolean in [(1, True), (0, False)]:
        x, y = fact(value=numeric), fact(value=boolean)
        out = [attempt(lambda rs=rs: snap(rs)) for rs in [[x, y], [y, x]]]
        record("boolean_numeric_collision_" + str(numeric), "duplicate_identity",
               "Boolean and numeric values claiming the same version conflict identically in either order", out,
               all(refused(r, "conflicting_source_version") for r in out),
               "boolean_numeric_duplicate_order_dependence" if numeric == 1 else None)
    x, y = fact(value=2**53), fact(value=2**53+1)
    out = [attempt(lambda rs=rs: snap(rs)) for rs in [[x, y], [y, x]]]
    record("adjacent_large_integer_duplicate_collision", "duplicate_identity",
           "2**53 and 2**53+1 remain distinct values and both duplicate orders fail closed", out,
           all(refused(r, "conflicting_source_version") for r in out))
    large = snap([fact(value=2**53), fact("000001.SZ", 2**53+1)])
    ranks = normal(large)
    record("adjacent_large_integer_distinct_issuer_order", "duplicate_identity",
           "Distinct representable JSON integers retain strict order through normalization",
           {"selected": large["selected"], "ranks": ranks}, ranks == {"600000.SS": 0.0, "000001.SZ": 1.0})
    exact = snap([a, b, deepcopy(a)])
    record("exact_duplicate_coalescing", "duplicate_identity", "Exact repeated records preserve the complete result", exact, exact == base)
    non_objects = [attempt(lambda value=value: snap([a, value])) for value in [None, 1, "record", []]]
    record("source_non_object_refused", "source_identity", "The explicit new record-object guard gives a defined refusal before reading malformed row fields", non_objects,
           all(refused(out, "source_record_not_object") for out in non_objects))

    for label, update, original_case in [
        ("revision_type", {"revision": "bad"}, "future_malformed_revision_type"),
        ("missing_ticker", {"ticker": None}, "future_malformed_missing_ticker"),
        ("empty_source_id", {"source_record_id": ""}, "future_malformed_empty_source_id"),
        ("boolean_revision", {"revision": True}, None),
        ("missing_family", {"family": None}, None),
        ("whitespace_ticker", {"ticker": "600111.SS "}, None),
        ("metadata_objects", {"unit": [], "feature_contract_id": {}}, None),
    ]:
        future = fact("600111.SS", True, first_seen_at="2026-10-09T09:00:00Z", published_at="2026-10-09T08:30:00Z")
        future.update(update)
        out = [attempt(lambda rs=rs: snap(rs)) for rs in [[a, b, future], [future, b, a]]]
        holds = all("returned" in r and r["returned"]["selected_input_digest"] == base["selected_input_digest"] and normal(r["returned"]) == normal(base) for r in out)
        record("future_malformed_" + label, "cutoff_noninterference",
               "Provably future availability excludes a row before unrelated identity, payload or feature metadata can affect past selection or normalization", out, holds, original_case)
    for label, clocks in [
        ("future_publication_missing_first_seen", {"published_at": "2026-10-09T09:00:00Z", "first_seen_at": None}),
        ("future_first_seen_invalid_publication", {"published_at": "invalid", "first_seen_at": "2026-10-09T09:00:00Z"}),
    ]:
        future = dict(a, revision="bad", **clocks)
        out = attempt(lambda: snap([a, b, future]))
        record(label, "cutoff_noninterference", "Either valid future availability clock suffices to prove nonavailability at the cutoff", out,
               out.get("returned", {}).get("selected_input_digest") == base["selected_input_digest"])

    for label, effective, reason in [("missing", None, "timestamp_missing"), ("invalid", "not-a-time", "timestamp_invalid"),
                                      ("naive", "2026-10-09T07:00:00", "timestamp_requires_timezone")]:
        retraction = dict(a, revision=1, status="retracted", value=None, effective_from=effective)
        out = [attempt(lambda rs=rs: snap(rs)) for rs in [[a, retraction], [retraction, a]]]
        holds = all("returned" in r and not r["returned"]["selected"] and len(r["returned"]["suppressed"]) == 1 and r["returned"]["suppressed"][0]["reason"] == reason for r in out)
        record("known_retraction_" + label + "_applicability", "revision_suppression",
               "A known higher retraction with malformed applicability suppresses the observation in every arrival order", out, holds,
               "known_retraction_" + label + "_applicability_resurrects")
    future_effective = dict(a, revision=1, value=8, effective_from="2026-10-10T00:00:00Z")
    correction = dict(a, revision=1, value=8)
    final = dict(a, revision=2, status="retracted", value=None)
    expected_single = snap([a])["selected_input_digest"]
    out = [snap([a, future_effective]), snap([future_effective, a])]
    record("valid_future_applicability_keeps_old_effective_value", "revision_suppression",
           "A known revision whose valid applicability is after the decision does not suppress the effective prior value", out,
           all(r["selected_input_digest"] == expected_single for r in out))
    permutation_results = [snap(list(rows)) for rows in itertools.permutations([a, correction, final])]
    record("known_revision_retraction_all_six_permutations", "revision_suppression",
           "Highest known revision and retraction suppression are independent of input order", permutation_results,
           all(not r["selected"] and r["suppressed"][0]["identity"][-1] == 2 and r["suppressed"][0]["reason"] == "source_retracted" for r in permutation_results))

    for label, expected in [("missing", None), ("malformed", "not-a-session"), ("impossible_date", "2026-02-30"),
                            ("not_leap_year", "2026-02-29"), ("un-padded", "2026-1-09"), ("datetime", "2026-10-09T00:00:00Z")]:
        out = attempt(lambda value=expected: snapshot([dict(a, observation_session=value)], CUTOFF, expected_sessions={"valuation": value}))
        record("invalid_expected_session_" + label, "session_identity", "An invalid calendar-date identity cannot qualify merely by matching itself", out,
               refused(out, "session_identity_invalid"), "invalid_expected_and_observed_session_" + label if label in {"missing", "malformed"} else None)
    observed_bad = snap([dict(a, observation_session="2026-02-30")])
    record("invalid_observed_session_suppression", "session_identity", "Invalid row session syntax suppresses the chosen version", observed_bad,
           not observed_bad["selected"] and observed_bad["suppressed"][0]["reason"] == "session_identity_invalid")
    leap = snapshot([dict(a, observation_session="2024-02-29")], CUTOFF, expected_sessions={"valuation": "2024-02-29"})
    record("valid_calendar_date_syntax_only", "session_identity", "Valid leap-day syntax is accepted when supplied by the caller; calendar correctness remains a source-owner premise", leap, len(leap["selected"]) == 1)
    wrong_session = snap([dict(a, observation_session="2026-10-08")])
    record("wrong_source_session_suppressed", "session_identity", "A syntactically valid but mismatched observation session is refused", wrong_session,
           not wrong_session["selected"] and wrong_session["suppressed"][0]["reason"] == "wrong_observation_session")

    periodic_override = snap([dict(a, cadence="periodic", observation_session="2026-01-02")])
    record("session_family_cannot_self_declare_periodic", "owner_cadence", "The row cannot override the family owner's session contract", periodic_override,
           not periodic_override["selected"] and periodic_override["suppressed"][0]["reason"] == "cadence_unqualified",
           "row_cadence_can_bypass_family_session_contract")
    periodic = fact(family="filing", cadence="periodic", observation_session="2026-06-30", published_at="2026-08-01T07:00:00Z", first_seen_at="2026-08-01T07:01:00Z", effective_from="2026-08-01T07:00:00Z")
    explicit = snap([periodic], periodic_families={"filing"})
    record("explicit_long_lived_periodic_family", "owner_cadence", "An owner-declared periodic observation remains valid until explicit expiry/supersession", explicit, len(explicit["selected"]) == 1)
    undeclared = snap([periodic])
    record("undeclared_periodic_family_refused", "owner_cadence", "A source family cannot declare its own permission through a row", undeclared,
           not undeclared["selected"] and undeclared["suppressed"][0]["reason"] == "source_family_unqualified")
    for label, periodic_families in [("conflicting", {"valuation"}), ("string", "filing"), ("null", None), ("scalar", 1), ("nested_list", [["filing"]])]:
        out = attempt(lambda value=periodic_families: snap([a], periodic_families=value))
        record("invalid_owner_periodic_contract_" + label, "owner_cadence",
               "Malformed or conflicting caller-owned cadence configuration is refused with the defined contract exception", out,
               refused(out, "periodic_family_contract_invalid"))

    for label, ticker in [("trailing_space", "600000.SS "), ("leading_space", " 600000.SS"), ("lowercase_suffix", "600000.ss"),
                          ("missing_exchange", "600000"), ("invalid_exchange", "600000.XY"), ("too_short", "60000.SS")]:
        out = attempt(lambda value=ticker: snap([a, b, dict(a, ticker=value)]))
        record("canonical_source_ticker_" + label, "issuer_identity", "Malformed issuer aliases cannot enter the selected normalization population", out,
               refused(out), "whitespace_issuer_alias_changes_normalization" if label == "trailing_space" else None)
    for ticker in ["600000.SS", "000001.SZ", "430001.BJ"]:
        out = snap([fact(ticker)])
        record("canonical_ticker_positive_" + ticker, "issuer_identity", "Each supported canonical exchange syntax remains admitted", out, len(out["selected"]) == 1)

    huge_rows = deepcopy(candidates); huge_rows[0]["intel"] = 10**400
    out = attempt(lambda: order(huge_rows))
    record("huge_intelligence_atomic_fallback", "numeric_validity", "Unrepresentable intelligence triggers the complete V3 fallback", out,
           out.get("returned", {}).get("mode") == "v3_atomic_fallback" and out.get("returned", {}).get("ordered") == incumbent,
           "large_json_integer_breaks_atomic_fallback")
    out = attempt(lambda: snap([a, dict(a, revision=1, value=10**400)]))
    record("huge_known_revision_suppression", "numeric_validity", "An unrepresentable latest source value suppresses the older observation within the contract error model", out,
           "returned" in out and not out["returned"]["selected"] and out["returned"]["suppressed"][0]["reason"] == "not_finite_json_number",
           "large_json_integer_breaks_known_revision_suppression")
    for label, value in [("zero", 0), ("negative", -0.25), ("finite_fraction", 1.25), ("large_finite_integer", 10**100)]:
        out = snap([fact(value=value)])
        record("finite_source_numeric_" + label, "numeric_validity", "Finite numeric source payload remains valid under its caller-owned feature contract", out,
               len(out["selected"]) == 1 and out["selected"][0]["value"] == value)
    # Coverage must be evaluated before either cap, even for a name that would
    # otherwise sit outside the chosen shortlist.
    below_cap = deepcopy(candidates)
    selected = set(order(candidates)["selected"])
    hidden = next(r for r in below_cap if r["ticker"] not in selected)
    hidden["intel"] = None
    out = order(below_cap)
    record("qualified_missing_below_cap_still_invalidates_coverage", "qualified_pre_cap",
           "An invalid qualified name excluded by caps still forces the whole eligible population to V3",
           {"invalid_ticker": hidden["ticker"], "mode": out["mode"], "invalid": out["invalid"]},
           out["mode"] == "v3_atomic_fallback" and out["ordered"] == incumbent)

    record("homogeneous_normalization_positive", "normalization", "Valid aggregated homogeneous features produce the expected ranks", normal(base),
           normal(base) == {"600000.SS": 0.0, "000001.SZ": 1.0})
    for field, value, label in [("family", "margin", "mixed_family"), ("unit", "CNY", "mixed_unit"),
                                ("feature_contract_id", "valuation/other/v2", "mixed_feature_contract")]:
        second = dict(b, **{field: value})
        if field == "family": second["observation_session"] = "2026-10-08"
        mixed = snap([a, second])
        out = attempt(lambda s=mixed: normal(s))
        record("normalization_" + label, "normalization", "Cross-sectional normalization refuses incompatible feature identities", out,
               refused(out, "normalization_requires_homogeneous_feature_contract"),
               "normalization_accepts_incompatible_feed_families" if field == "family" else None)
    for field in ["unit", "feature_contract_id"]:
        for label, value in [("missing", None), ("blank", ""), ("whitespace", " invalid "), ("boolean", True), ("list", []), ("object", {})]:
            chosen = snap([dict(a, **{field: value}), dict(b, **{field: value})])
            out = attempt(lambda s=chosen: normal(s))
            record("normalization_" + field + "_" + label, "normalization",
                   "Malformed homogeneous metadata is refused with the defined contract exception rather than bypassing or crashing validation", out,
                   refused(out, "normalization_requires_homogeneous_feature_contract"))
        changed = snap([dict(a, **{field: "other_valid_identity"}), dict(b, **{field: "other_valid_identity"})])
        record("fingerprint_captures_" + field, "fingerprint", "Changing feature semantics changes the selected-input identity even when values/ranks are identical",
               {"base_digest": base["selected_input_digest"], "changed_digest": changed["selected_input_digest"], "same_ranks": normal(changed) == normal(base)},
               changed["selected_input_digest"] != base["selected_input_digest"] and normal(changed) == normal(base))
    many = snap([a, b, dict(a, source_record_id="separate-observation")])
    out = attempt(lambda: normal(many))
    record("normalization_requires_qualified_aggregation", "normalization", "Multiple observations for one issuer require the existing aggregation owner before normalization", out,
           refused(out, "normalization_requires_aggregated_unique_ticker_features"))

    contradictory = [dict(ticker="600000.SS", qualified=True, score=10, score_rank=1, intel=0, intel_basis="measured", sector="A"),
                     dict(ticker="000001.SZ", qualified=True, score=90, score_rank=2, intel=0, intel_basis="measured", sector="B")]
    z = order(contradictory)
    contradictory[0]["intel_basis"] = "missing"
    v = order(contradictory)
    mixed = [dict(r, intelligence_generation="A" if i % 2 else "B") for i, r in enumerate(candidates)]
    g = order(mixed)
    premises = {"score_rank_coherence": {"current_dataset_verified": incumbent == score_order, "contradictory_zero_order": z["ordered"], "contradictory_fallback_order": v["ordered"],
                                           "required_owner": "Existing score/generation owner binds coherent incumbent score/rank before ordering."},
                "generation_compatibility": {"mixed_labels_still_numeric_complete": g["mode"] == "intelligence_atomic", "numeric_helper_does_not_validate_labels": True,
                                               "required_owner": "Existing generation owner binds compatible qualification, score/rank, source inputs, normalization population and calibration receipt."},
                "source_calendar": "Calendar-date syntax does not certify the trading session; expected sessions remain caller/source-owner premises.",
                "source_history": "Missing publication/first-seen provenance still cannot establish complete historical availability or authoritative revision history."}

    duplicates = json.loads(blobs["analyst_duplicates.json"])
    group_sizes = [len({json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) for v in r["payloads"]}) for r in duplicates["duplicates"]]
    dupe_control = {"duplicate_groups": len(group_sizes), "independent_payload_equality": bool(group_sizes) and set(group_sizes) == {1},
                    "source_receipt_conflicting_groups": duplicates["conflicting_payload_groups"], "source_receipt_changed_consensus": duplicates["changed_consensus_blocks"],
                    "source_receipt_changed_raw_scores": duplicates["changed_raw_rating_scores"], "source_receipt_changed_percentiles": duplicates["changed_rank_percentiles"],
                    "evidence_limit": "Payload equality is independently checked. Full remote reader reversal is the existing hash-bound receipt, not a new remote replay."}
    record("actual_analyst_duplicates_remain_identical", "positive_control", "No corruption is inferred from the actual identical duplicate groups", dupe_control,
           len(group_sizes) == 475 and set(group_sizes) == {1} and duplicates["conflicting_payload_groups"] == duplicates["changed_consensus_blocks"] == duplicates["changed_raw_rating_scores"] == duplicates["changed_rank_percentiles"] == 0)

    for name, value in blobs.items():
        check(sha((LAB / name).read_bytes()) == sha(value), "Repaired snapshot mutated: " + name)
    for name, expected in original_hashes.items():
        check(sha((INITIAL / name).read_bytes()) == expected, "Initial review changed during acceptance: " + name)
    for name, expected in prior_hashes.items():
        check(sha((prior_acceptance / name).read_bytes()) == expected, "Prior repaired acceptance changed during final acceptance: " + name)
    failed = [r for r in tests if not r["passed"]]
    original_failed_names = {r["name"] for r in json.loads((INITIAL / "CHALLENGE_RESULTS.json").read_text())["tests"] if r["category"] == "demonstrated_failure" and not r["invariant_holds"]}
    replayed = {r["original_case"] for r in tests if r["original_case"] in original_failed_names}
    check(replayed == original_failed_names, "An original failure was not replayed")
    closed = [r for r in tests if r["original_case"] in original_failed_names and r["passed"]]
    result = {"schema": "intelligence_repaired_independent_acceptance_v1", "status": "ACCEPTED_BOUNDED_RESEARCH_CONTRACT" if not failed else "REMAINING_BOUNDED_CONTRACT_GAPS",
              "source_sha": SOURCE_PIN, "repaired_files_sha256": pins, "initial_review_manifest_sha256": freeze["initial_review_manifest_sha256"],
              "acceptance_design_sha256": sha((HERE / "ACCEPTANCE_DESIGN.md").read_bytes()), "input_freeze_sha256": sha(freeze_bytes),
              "acceptance_script_sha256": sha(Path(__file__).read_bytes()),
              "principal_suite": {"check_n": 56, "result_byte_identical": True, "result_sha256": sha(replay_bytes), "stdout": stdout.getvalue().strip()},
              "test_n": len(tests), "passed_n": len(tests)-len(failed), "failed_n": len(failed),
              "original_failure_variants": {"n": len(original_failed_names), "replayed_n": len(replayed), "closed_n": len(closed)},
              "failed_case_names": [r["name"] for r in failed], "tests": tests, "upstream_premises": premises,
              "actual_duplicate_control": dupe_control,
              "custody": {"initial_review_files_unchanged": True, "initial_review_file_n": len(original_hashes), "repaired_snapshot_unchanged": True,
                          "prior_repaired_acceptance_unchanged": True, "prior_repaired_acceptance_file_n": len(prior_hashes),
                          "principal_lab_mutations": 0, "matched_control_mutations": 0, "production_effects": 0, "vendor_calls": 0, "remote_replays": 0},
              "limits": ["Synthetic repair acceptance is not evidence of current-data corruption, investment improvement or production time-qualified coverage.",
                         "No source store, ranking activation, production identity, generation protocol or authoritative revision history is installed by this laboratory.",
                         "Selected-input digest is an input-fingerprint example; the existing generation owner must bind full upstream contracts."]}
    (HERE / "ACCEPTANCE_RESULTS.json").write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "test_n", "passed_n", "failed_n", "original_failure_variants", "failed_case_names"]}, indent=2))


if __name__ == "__main__":
    main()
