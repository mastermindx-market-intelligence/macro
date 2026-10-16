#!/usr/bin/env python3
"""Independent hostile acceptance of an exact repaired integration package.

The producer's test runner is not imported. Review-owned payloads pass through
the real pinned parser, state machine and reconciliation bodies. Final acceptance
also requires a hash-bound independent native-Parquet execution receipt.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import argparse
import json
import socket
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from review_support import (DEEP, PIN, NATIVE_BUNDLE, capture, hash_file, load_native,
                            load_subject, read, unchanged_originals, verify_manifest)
import independent_fixture as I

CHECKS = []
EVIDENCE = {}


def check(name, condition, details=None):
    CHECKS.append({"name": name, "status": "PASS" if condition else "FAIL",
                   "details": details})
    if not condition:
        raise AssertionError(name)


def refusal(name, operation, reasons):
    got = capture(operation)
    allowed = {reasons} if isinstance(reasons, str) else set(reasons)
    check(name, got.get("exception_class") == "Refused" and got.get("reason") in allowed,
          {k: v for k, v in got.items() if k != "value"})
    return {k: v for k, v in got.items() if k != "value"}


def no_network(*args, **kwargs):
    raise RuntimeError("Network disabled during independent repair acceptance")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--manifest-sha")
    parser.add_argument("--parquet-receipt", type=Path)
    args = parser.parse_args()
    candidate = DEEP / "repairs/integration_contract"
    protected = unchanged_originals()
    check("all_original_lab_and_review_payloads_verified", bool(protected))
    if args.manifest is not None:
        if not args.manifest_sha:
            raise ValueError("An exact expected candidate manifest SHA-256 is required")
        manifest, candidate_files = verify_manifest(args.manifest, args.manifest_sha)
    else:
        manifest, candidate_files = None, None
    before = {name: hash_file(candidate / name)
              for name in ("contract_prototype.py", "pinned_quote_adapter.py")}
    modules, native_ids = load_native()
    B = load_subject(candidate / "contract_prototype.py")
    adapter = (candidate / "pinned_quote_adapter.py").read_bytes()
    check("pinned_quote_adapter_hash", sha256(adapter).hexdigest()
          == "bd8bfd85bf4ff1279d564220b7f3f8b8b4e5f7263323252ae6489ed5163d1074")
    resolver = B.SyntheticQuoteResolver(adapter)
    check("pinned_quote_adapter_git_object", resolver.contract["adapter_git_blob"]
          == __import__("hashlib").sha1(b"blob " + str(len(adapter)).encode() + b"\0" + adapter).hexdigest())
    LS = modules["engine/prophet_live/live_states.py"]
    CS = modules["engine/prophet_live/cn_states.py"]
    R2 = modules["engine/prophet_live/r2io.py"]
    CR = modules["engine/prophet_live/cn_reconcile.py"]
    clock = modules["engine/prophet_live/cn_clock.py"]
    old_fixture = read(DEEP / "integration_lab/integration_fixture.json")
    fixture, arts, quote_sets, cfg = I.build(B, modules, resolver, old_fixture)

    def ingest(*, store=None, prior=None, canonical=True):
        return I.ingest(B, modules, resolver, fixture, store=store,
                        existing=prior, canonical=canonical)

    def fresh():
        return I.store_for(B, R2, fixture)

    def evaluate(quotes, now=I.at(2), previous=None):
        return B.evaluate_checked(CS.evaluate, LS, clock, fixture["base_pack"],
                                  quotes, previous, now=now, cfg=cfg, delay_min=0,
                                  quote_resolver=resolver)

    def put_events(store, artifact, events):
        doc = B.envelope(artifact, events, fixture["base_pack"])
        key = B.spool_key(doc, R2)
        store.put(key, doc)
        return key, doc

    baseline, base_receipt = ingest()
    check("independent_native_passes", [len(a["events"]) for a in arts] == [3, 1, 0, 0])
    check("independent_native_daily_rows", len(baseline) == 4)
    check("archived_prior_generation_survives_current_rollover",
          fixture["base_pack"]["pack_id"] != fixture["settlement_pack"]["pack_id"]
          and all(row["first_pack_id"] == fixture["base_pack"]["pack_id"] for row in baseline))
    verdicts = {row["ticker"]: row["confirmed"] for row in baseline}
    check("settlement_gate_verdict_authority", verdicts == {
        "002460.SZ": True, "300750.SZ": True, "603799.SS": False})
    check("canonical_membership_authority", base_receipt["receipt"]["confirmed"]
          == ["002460.SZ", "300750.SZ"] and base_receipt["receipt"]["dropped"] == ["603799.SS"])
    check("canonical_exact_byte_binding", base_receipt["canonical_board_sha256"]
          == sha256(fixture["canonical_board_utf8"].encode()).hexdigest()
          == fixture["settlement_pack"]["source_board"]["artifact_sha256"])
    check("synthetic_source_qualification_is_explicit", all(
        row["price_adjustment"] == "unadjusted_research_fixture"
        and row["quote_contract_id"] == resolver.contract_id for row in baseline))
    replay, _ = ingest(prior=deepcopy(baseline))
    check("complete_replay_idempotence", B.encoded(replay) == B.encoded(baseline))
    EVIDENCE["positive_three_join"] = {"rows": baseline, "receipt": base_receipt,
                                       "native_event_counts": [3, 1, 0, 0]}

    # F1: full-key disappearance is tested separately from partial ID loss.
    event_keys = sorted(key for key, doc in fixture["events"].items() if doc["events"])
    omissions = []
    for label, keys in (("first_transition_object", event_keys[:1]),
                        ("every_transition_object", event_keys)):
        store = fresh()
        for key in keys:
            del store.objects[key]
        got = refusal("F1_" + label, lambda store=store: ingest(store=store, prior=baseline),
                      "spool_regression")
        omissions.append({"variant": label, "omitted_keys": keys, "result": got})
    closes_only = fresh()
    for key in event_keys:
        del closes_only.objects[key]
    empty_rows, empty_receipt = ingest(store=closes_only)
    check("new_empty_session_with_valid_close_is_supported",
          empty_rows == [] and empty_receipt["distinct_events"] == 0)
    partial = deepcopy(baseline)
    partial[0]["event_ids"].append("a" * 64)
    partial[0]["occurrences"] += 1
    refusal("F1_partial_id_regression", lambda: ingest(prior=partial), "spool_regression")
    EVIDENCE["F1"] = omissions

    # F2: fixed conflicting economics; nonce alone changes relative key order.
    latest = deepcopy(max((d for d in fixture["events"].values() if d["close_board"]),
                          key=lambda d: B.stamp(d["built_at"])))
    fixed_key = B.spool_key(latest, R2)
    alternate = deepcopy(latest)
    for lane in alternate["close_board"]["lanes"].values():
        lane[:] = [row for row in lane if row["ticker"] != "603799.SS"]
    variants = {}
    for nonce in range(1024):
        doc = deepcopy(alternate)
        doc["independent_review_nonce"] = nonce
        key = B.spool_key(doc, R2)
        relation = "before" if key < fixed_key else "after"
        variants.setdefault(relation, (key, doc))
        if len(variants) == 2:
            break
    check("F2_both_inert_nonce_order_variants_found", len(variants) == 2)
    close_conflicts = []
    for relation, (key, doc) in sorted(variants.items()):
        store = fresh()
        store.put(key, doc)
        got = refusal("F2_conflicting_close_" + relation,
                      lambda store=store: ingest(store=store), "conflicting_equal_time_close_evidence")
        close_conflicts.append({"relative_order": relation, "fixed_key": fixed_key,
                                "alternative_key": key, "nonce": doc["independent_review_nonce"],
                                "fixed_economics_sha256": B.digest(B.close_economics(latest["close_board"])),
                                "alternative_economics_sha256": B.digest(B.close_economics(doc["close_board"])),
                                "result": got})
    equivalent = deepcopy(latest)
    equivalent["display_note"] = "independent equivalent-envelope review"
    for rows in equivalent["close_board"]["lanes"].values():
        rows.reverse()
        for row in rows:
            row["display_note"] = "non-economic decoration"
    equivalent_key = B.spool_key(equivalent, R2)
    equivalent_store = fresh()
    equivalent_store.put(equivalent_key, equivalent)
    eq_rows, eq_receipt = ingest(store=equivalent_store, prior=baseline)
    check("equivalent_close_evidence_preserves_rows_and_membership",
          B.encoded(eq_rows) == B.encoded(baseline)
          and eq_receipt["receipt"] == base_receipt["receipt"])
    check("equivalent_close_evidence_retains_both_object_identities",
          eq_receipt["selected_close_evidence"]["object_keys"] == sorted([fixed_key, equivalent_key]))
    EVIDENCE["F2"] = {"conflicting_variants": close_conflicts,
                       "equivalent_observation_receipt": eq_receipt["selected_close_evidence"]}

    # F3: a real pinned parser runs, but these source bytes remain a fixture.
    first_quotes = deepcopy(quote_sets[I.at(2).isoformat()])
    qualification_cases = []
    for adjustment in (None, "split_and_dividend_adjusted", "unadjusted_vendor_print"):
        quotes = deepcopy(first_quotes)
        for row in quotes.values():
            row.pop("source_evidence")
            if adjustment is None:
                row.pop("price_adjustment")
            else:
                row["price_adjustment"] = adjustment
        art = evaluate(quotes)
        check("F3_unqualified_declaration_" + str(adjustment), not art["events"]
              and set(art["meta"]["quote_rejections"]) == set(quotes)
              and set(art["meta"]["quote_rejections"].values()) == {"quote_basis_evidence_unavailable"})
        qualification_cases.append({"input_adjustment": adjustment, "events": len(art["events"]),
                                    "quote_rejections": art["meta"]["quote_rejections"]})
    fake_flag = deepcopy(first_quotes)
    for row in fake_flag.values():
        row["source_evidence"] = {"qualified": True}
    fake_art = evaluate(fake_flag)
    check("caller_qualification_boolean_has_no_authority", not fake_art["events"]
          and set(fake_art["meta"]["quote_rejections"].values()) == {"unsupported_quote_source_contract"})
    altered_quote = deepcopy(first_quotes)
    altered_quote["002460.SZ"]["price"] += 1
    bad_art = evaluate(altered_quote)
    check("quote_price_must_equal_replayed_payload", bad_art["meta"]["quote_rejections"]
          == {"002460.SZ": "quote_disagrees_with_source_payload"}
          and {e["ticker"] for e in bad_art["events"]} == {"300750.SZ", "603799.SS"})
    raw_a = fixture["quote_payloads_utf8"][I.at(2).isoformat()].encode()
    raw_b = json.dumps(json.loads(raw_a), indent=2, ensure_ascii=False).encode()
    byte_variant = resolver.quotes(raw_b, recorded_at=I.at(2))
    source_a = first_quotes["002460.SZ"]["source_evidence"]
    source_b = byte_variant["002460.SZ"]["source_evidence"]
    check("exact_source_bytes_remain_distinct", raw_a != raw_b
          and source_a["payload_sha256"] == sha256(raw_a).hexdigest()
          and source_b["payload_sha256"] == sha256(raw_b).hexdigest()
          and source_a["payload_sha256"] != source_b["payload_sha256"]
          and source_a["quote_record_sha256"] == source_b["quote_record_sha256"]
          and source_b["payload_utf8"].encode() == raw_b)
    unchanged_hash_bad_text = deepcopy(first_quotes)
    unchanged_hash_bad_text["002460.SZ"]["source_evidence"]["payload_utf8"] = raw_b.decode()
    bad_text_art = evaluate(unchanged_hash_bad_text)
    check("source_text_cannot_change_under_existing_byte_hash",
          bad_text_art["meta"]["quote_rejections"] == {"002460.SZ": "quote_payload_identity_mismatch"})
    wrong_event = deepcopy(arts[0]["events"][0])
    wrong_event["price"] += 1
    wrong_event.pop("event_id")
    wrong_event["event_id"] = B.digest({"pack_id": fixture["base_pack"]["pack_id"], **wrong_event})
    wrong_store = fresh()
    for key in fixture["events"]:
        del wrong_store.objects[key]
    put_events(wrong_store, arts[0], [wrong_event])
    refusal("F3_rehashed_event_price_still_binds_source", lambda: ingest(store=wrong_store),
            "event_quote_source_disagreement")
    EVIDENCE["F3"] = {"unqualified_inputs": qualification_cases,
                       "byte_variant_payload_hashes": [source_a["payload_sha256"], source_b["payload_sha256"]],
                       "common_native_record_sha256": source_a["quote_record_sha256"],
                       "contract": resolver.contract}

    # F4 core validation; actual readable Parquet cases are independently run
    # by the companion helper and required for final acceptance below.
    duplicate = deepcopy(baseline[0])
    duplicate["event_ids"].append("d" * 64)
    duplicate["occurrences"] += 1
    duplicate["last_ts"] = "2026-10-12T02:01:00Z"
    for label, prior in (("conflict_last", [*deepcopy(baseline), duplicate]),
                         ("conflict_first", [duplicate, *deepcopy(baseline)]),
                         ("exact_duplicate", [*deepcopy(baseline), deepcopy(baseline[0])])):
        refusal("F4_" + label, lambda prior=prior: ingest(prior=prior), "duplicate_existing_daily_key")

    # F5 and F6 distinguish invalid, missing and valid measured zero.
    for score in (-1, 100.01, 0, 100):
        pack = deepcopy(fixture["base_pack"])
        pack["names"]["002460.SZ"]["frozen"]["score"] = score
        pack.pop("pack_id")
        pack["pack_id"] = B.digest(pack)
        if score < 0 or score > 100:
            refusal("F5_standalone_score_" + str(score), lambda pack=pack: B.validate_pack(pack),
                    "invalid_frozen_score")
        else:
            B.validate_pack(pack)
            check("F5_valid_boundary_score_" + str(score), True)
    huge = 10 ** 400
    check("F6_huge_integer_numeric_predicate_is_total", B.finite(huge, positive=True) is False)
    huge_quotes = deepcopy(first_quotes)
    huge_quotes["002460.SZ"]["price"] = huge
    huge_art = evaluate(huge_quotes)
    check("F6_bad_quote_does_not_abort_valid_peers", huge_art["meta"]["quote_rejections"]
          == {"002460.SZ": "invalid_quote_price"}
          and {e["ticker"] for e in huge_art["events"]} == {"300750.SZ", "603799.SS"})
    huge_payload = json.loads(raw_a)
    huge_payload["spark"]["result"][0]["response"][0]["meta"]["regularMarketPrice"] = huge
    refusal("huge_provider_payload_takes_typed_refusal",
            lambda: resolver.quotes(B.encoded(huge_payload), recorded_at=I.at(2)), "invalid_quote_payload_price")

    # F7: authenticate the projection against resolved history, even if someone
    # recomputes its local content digest after changing a copied field.
    immutable_cases = []
    mutations = {"first_px": baseline[0]["first_px"] + 1,
                 "first_quote_ts": "2026-10-12T02:00:01+00:00",
                 "quote_payload_sha256": "a" * 64,
                 "first_quote_record_sha256": "b" * 64,
                 "source_board_definition": "forged-definition",
                 "cross_basis_close": baseline[0]["cross_basis_close"] + 1,
                 "first_quote_age_min": baseline[0]["first_quote_age_min"] + 1,
                 "from_state": "forged-state"}
    for field, value in mutations.items():
        prior = deepcopy(baseline)
        prior[0][field] = value
        got = refusal("F7_immutable_" + field, lambda prior=prior: ingest(prior=prior),
                      "existing_first_observation_conflict")
        immutable_cases.append({"field": field, "proposed_value": value, "result": got})
    rehashed = deepcopy(baseline)
    rehashed[0]["first_px"] += 1
    rehashed[0]["first_observation_sha256"] = B.digest(B.first_observation(rehashed[0]))
    refusal("F7_rehash_cannot_authorize_first_price_rewrite", lambda: ingest(prior=rehashed),
            "existing_first_observation_conflict")
    EVIDENCE["F7"] = immutable_cases

    # Compatibility: older native history is retained without invented claims.
    legacy = {"schema": CR.FORWARD_SCHEMA, "date": "2026-10-09", "ticker": "002460.SZ",
              "kind": "forming", "first_ts": "2026-10-09T02:00:00Z", "first_px": 10.0,
              "cross_px": 10.0, "last_ts": "2026-10-09T02:05:00Z", "last_px": 10.1,
              "occurrences": 2, "confirmed": None, "close_same_day": None,
              "next_close_fill": None, "independent_legacy_note": "pre-existing native history"}
    legacy_rows, _ = ingest(prior=[deepcopy(legacy), *deepcopy(baseline)])
    old_row = next(r for r in legacy_rows if r["date"] == legacy["date"])
    check("older_legacy_native_row_is_carried_unchanged", B.encoded(old_row) == B.encoded(legacy)
          and "ingest_contract" not in old_row and "first_event_id" not in old_row)
    target_legacy = {**legacy, "date": I.SESSION,
                     "first_ts": "2026-10-12T02:00:00Z", "last_ts": "2026-10-12T02:05:00Z"}
    refusal("target_session_unbound_history_requires_migration", lambda: ingest(prior=[target_legacy]),
            "legacy_unbound_row")
    # Real native dark-to-forming transition, with a strictly later clock.
    dark = evaluate({}, now=I.at(2, 9), previous=arts[1])
    later_raw = B.encoded(I.payload(fixture["base_pack"], fixture["prices"], I.at(2, 10)))
    later_quotes = resolver.quotes(later_raw, recorded_at=I.at(2, 10))
    later = evaluate(later_quotes, now=I.at(2, 10), previous=dark)
    repeat = next(e for e in later["events"] if e["ticker"] == "002460.SZ" and e["kind"] == "forming")
    check("repeat_is_a_native_later_transition", repeat.get("from") == "dark"
          and repeat["ts"] == "2026-10-12T02:10:00Z")
    repeat_store = fresh()
    put_events(repeat_store, later, [repeat])
    repeat_rows, _ = ingest(store=repeat_store, prior=baseline)
    target = next(r for r in repeat_rows if r["ticker"] == "002460.SZ" and r["kind"] == "forming")
    original = next(r for r in baseline if r["ticker"] == "002460.SZ" and r["kind"] == "forming")
    check("native_repeat_updates_last_and_count_preserves_first", target["occurrences"] == 2
          and target["last_ts"] == repeat["ts"] and len(target["event_ids"]) == 2
          and B.first_observation(target) == B.first_observation(original)
          and target["first_observation_sha256"] == original["first_observation_sha256"])
    EVIDENCE["compatibility"] = {"legacy_row": old_row, "native_repeat_event": repeat,
                                  "repeat_row": target}

    # Additional authority boundary: equal event time cannot be ordered by hash.
    changed_prices = {**fixture["prices"], "002460.SZ": fixture["prices"]["002460.SZ"] + 0.0001}
    tie_quotes = resolver.quotes(B.encoded(I.payload(fixture["base_pack"], changed_prices, I.at(2))),
                                 recorded_at=I.at(2))
    tie_art = evaluate(tie_quotes)
    tie_event = next(e for e in tie_art["events"] if e["ticker"] == "002460.SZ")
    check("equal_time_conflict_uses_two_authentic_native_events", tie_event["ts"] == original["first_ts"]
          and tie_event["kind"] == original["kind"] and tie_event["price"] != original["first_px"])
    tie_store = fresh()
    tie_key, _ = put_events(tie_store, tie_art, [tie_event])
    tie_result = refusal("equal_time_first_event_conflict_refuses", lambda: ingest(store=tie_store),
                         "ambiguous_equal_time_events")
    duplicate_store = fresh()
    same_doc = deepcopy(fixture["events"][event_keys[0]])
    same_doc["independent_duplicate_envelope"] = True
    duplicate_store.put(B.spool_key(same_doc, R2), same_doc)
    same_rows, same_receipt = ingest(store=duplicate_store, prior=baseline)
    check("exact_event_id_replay_deduplicates_before_time_conflict", B.encoded(same_rows) == B.encoded(baseline)
          and same_receipt["distinct_events"] == 4)
    EVIDENCE["equal_time_first_event"] = {"alternative_key": tie_key,
                                          "alternative_native_event": tie_event, "result": tie_result}

    # Replay the two preserved pre-seal temporal falsifiers under the current
    # source contract, so schema refusal cannot masquerade as a time-rule fix.
    clock_challenges = read(HERE / "draft_challenges/CLOCK_EVIDENCE.json")
    clock_results = []
    for case in clock_challenges["cases"]:
        pack, doc = deepcopy(case["pack"]), deepcopy(case["envelope"])
        doc["schema"] = B.EVENT_SCHEMA
        for event in doc["events"]:
            receipt_at = B.stamp(event["source_evidence"]["recorded_at"])
            native_quotes = resolver.quotes(event["source_evidence"]["payload_utf8"].encode(),
                                             recorded_at=receipt_at)
            event["source_evidence"] = native_quotes[event["ticker"]]["source_evidence"]
            event["price_adjustment"] = resolver.adjustment
            event["quote_source"] = native_quotes[event["ticker"]]["source"]
            event.pop("event_id")
            event["event_id"] = B.digest({"pack_id": pack["pack_id"], **event})
        store = fresh()
        for key in fixture["events"]:
            del store.objects[key]
        store.put(B.pack_key(pack, R2), pack)
        store.put(B.spool_key(doc, R2), doc)
        reason = "future_quote_source_receipt" if case["id"] == "R-C1" else "future_pack_build"
        got = refusal("event_time_authority_" + case["id"], lambda store=store: ingest(store=store), reason)
        clock_results.append({"id": case["id"], "pack_id": pack["pack_id"],
                              "event_ts": doc["events"][0]["ts"],
                              "source_recorded_at": doc["events"][0]["source_evidence"]["recorded_at"],
                              "pack_built_at": pack["built_at"], "result": got})
    EVIDENCE["event_time_authorities"] = clock_results

    fixture["ledger"] = baseline
    fixture["reconciliation"] = base_receipt
    fixture["legacy_row"] = legacy
    fixture["repeat_envelope"] = B.envelope(later, [repeat], fixture["base_pack"])
    fixture["review_binding"] = {"candidate_inputs_sha256": before,
                                "native_bundle_sha256": NATIVE_BUNDLE,
                                "fixture_generator_sha256": hash_file(HERE / "independent_fixture.py"),
                                "original_fixture_sha256": hash_file(DEEP / "integration_lab/integration_fixture.json")}
    fixture_path = HERE / "independent_fixture.json"
    fixture_path.write_text(json.dumps(fixture, sort_keys=True, indent=2, allow_nan=False) + "\n")

    parquet = None
    if args.parquet_receipt:
        parquet = read(args.parquet_receipt)
        check("parquet_independent_helper_identity", parquet["helper_sha256"]
              == hash_file(HERE / "parquet_acceptance.py"))
        check("parquet_exact_candidate_and_fixture", parquet["candidate_inputs_sha256"] == before
              and parquet["fixture_sha256"] == hash_file(fixture_path)
              and parquet["native_bundle_sha256"] == NATIVE_BUNDLE)
        check("parquet_required_native_cases_pass", parquet["status"] == "PASS"
              and parquet["native_positive_write_count"] >= 2
              and len(parquet["refused_file_cases"]) == 4
              and all(row["writer_calls"] == 0 and row["before_sha256"] == row["after_sha256"]
                      for row in parquet["refused_file_cases"]))
        for relative, expected in parquet["retained_files_sha256"].items():
            check("retained_parquet_bytes_" + relative, hash_file(args.parquet_receipt.parent / relative) == expected)
    check("original_lab_and_review_unchanged_after_acceptance", unchanged_originals() == protected)
    for name, expected in before.items():
        check("candidate_unchanged_during_execution_" + name, hash_file(candidate / name) == expected)
    if args.manifest:
        _, after_files = verify_manifest(args.manifest, args.manifest_sha)
        check("exact_candidate_manifest_unchanged_after_execution", after_files == candidate_files)
    status = ("ACCEPTED_AS_BOUNDED_OFFLINE_RESEARCH_CONTRACT" if manifest and parquet
              else "CORE_PASS_PARQUET_PENDING" if manifest else "DRAFT_CORE_CHECKS_PASS_NOT_ACCEPTANCE")
    result = {"schema": "independent_integration_repair_acceptance/v1", "status": status,
              "study_pin": PIN, "reviewed_candidate_manifest_sha256": args.manifest_sha,
              "candidate_inputs_sha256": before, "candidate_manifest_files": candidate_files,
              "native_source_sha256": native_ids, "native_bundle_sha256": NATIVE_BUNDLE,
              "independent_fixture_sha256": hash_file(fixture_path),
              "review_script_sha256": hash_file(Path(__file__)),
              "review_support_sha256": hash_file(HERE / "review_support.py"),
              "fixture_generator_sha256": hash_file(HERE / "independent_fixture.py"),
              "protected_originals_sha256": protected, "evidence": EVIDENCE,
              "native_parquet_receipt_sha256": hash_file(args.parquet_receipt) if parquet else None,
              "native_parquet_execution": parquet, "passed_checks": len(CHECKS), "checks": CHECKS,
              "limits": ["Independent review-owned synthetic bytes and scenarios execute actual pinned parser/state/reconciliation bodies.",
                         "The producer runner is not imported; its manifest is verified as the exact reviewed package.",
                         "No historical natural occurrence, genuine provider adjustment declaration, market execution or fill is certified.",
                         "Native Parquet execution uses only a review-owned isolated temporary directory.",
                         "Scheduled production operation, real source custody and persistent storage guarantees remain implementation gates."],
              "effects": {"production_writes": False, "vendor_calls": False,
                          "network_disabled": True, "completed_labs_changed": False}}
    output = HERE / ("ACCEPTANCE_RESULTS.json" if manifest else "DRAFT_CORE_RESULTS.json")
    output.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": status, "checks": len(CHECKS), "fixture_sha256": hash_file(fixture_path),
                      "result_sha256": hash_file(output)}))


if __name__ == "__main__":
    with patch.object(socket.socket, "connect", no_network), patch.object(socket, "create_connection", no_network):
        main()
