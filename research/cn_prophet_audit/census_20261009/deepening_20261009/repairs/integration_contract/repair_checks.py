"""Discriminating repair controls, injected into the exact native offline run.

This file writes only into the runner's isolated output directory. It uses the
real native state machine and native Parquet writer supplied by the runner.
The retained cases are deltas from integration_fixture.json, not live inputs.
"""
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import json

from contract_prototype import (FIRST_OBSERVATION_FIELDS, INGEST_CONTRACT,
    SyntheticQuoteResolver, encoded, digest, envelope, evaluate_checked,
    finite, first_observation, normalize_storage, pack_key, reconcile_file,
    spool_key, stamp, validate_pack)


def run_repair_checks(*, check, refusal, ingest, store, pack, ledger, morning,
                      settled_at, quote_resolver, quotes_for, native_evaluate,
                      LS, clock, CR, RD, R2, pd, out, cfg):
    session = morning.date().isoformat()
    ticker = ledger[0]["ticker"]
    prefix = R2.CN_EVENTS_PREFIX + "/" + session + "/"
    event_keys = sorted(k for k in store.objects if k.startswith(prefix))
    active_keys = [k for k in event_keys if json.loads(store.objects[k])["events"]]
    close_keys = [k for k in event_keys if json.loads(store.objects[k]).get("close_board")]
    latest_key = max(close_keys, key=lambda k: stamp(json.loads(store.objects[k])["built_at"]))
    cases, parquet_receipts = [], []

    def store_delta(subject):
        return {"removed_objects": sorted(set(store.objects) - set(subject.objects)),
                "written_objects": {k: json.loads(v) for k, v in subject.objects.items()
                    if store.objects.get(k) != v}}

    def reject_ingest(name, reason, *, subject=store, prior=None):
        cases.append({"name": name, "expected": reason, **store_delta(subject),
                      "prior_rows": deepcopy(prior)})
        refusal(name, lambda: ingest(subject, prior=prior), reason)

    def publish(subject, doc):
        subject.objects[spool_key(doc, R2)] = encoded(doc)

    def reseal_event(ev, pid):
        ev.pop("event_id", None)
        ev["event_id"] = digest({"pack_id": pid, **ev})

    def reseal_pack(p):
        p.pop("pack_id", None)
        p["pack_id"] = digest(p)
        return p

    def checked(q, *, at=morning, previous=None, resolver=quote_resolver, p=pack):
        return evaluate_checked(native_evaluate, LS, clock, p, q, previous,
            now=at, cfg=cfg, delay_min=0, quote_resolver=resolver)

    # H1: support for every consumed event, even when its daily row disappears.
    for name, removed in (("vanished_daily_key_refuses", [active_keys[0]]),
                          ("all_transition_objects_vanished_refuses", active_keys)):
        missing = deepcopy(store)
        for key in removed:
            del missing.objects[key]
        reject_ingest(name, "spool_regression", subject=missing, prior=ledger)
    empty = deepcopy(store)
    for key in active_keys:
        del empty.objects[key]
    zero_rows, zero_receipt = ingest(empty)
    check("new_zero_event_session_with_close_remains_valid", zero_rows == []
          and zero_receipt["distinct_events"] == 0 and zero_receipt["close_board_available"])

    # H2: native keys must be unique before FIRST_WINS sees any existing rows.
    contradictory = deepcopy(ledger[0])
    contradictory["first_px"] += 1.0
    duplicate_cases = (
        ("conflicting_daily_keys_forward", deepcopy(ledger) + [contradictory]),
        ("conflicting_daily_keys_reverse", [contradictory] + deepcopy(ledger)),
        ("exact_duplicate_daily_key", deepcopy(ledger) + [deepcopy(ledger[0])]),
    )
    for name, prior in duplicate_cases:
        reject_ingest(name, "duplicate_existing_daily_key", prior=prior)
    for name, mutate, reason in (
        ("unknown_existing_schema", lambda r: r.update(schema="something_else/v1"), "invalid_existing_ledger_schema"),
        ("missing_existing_daily_key", lambda r: r.pop("ticker"), "invalid_existing_ledger_schema"),
        ("invalid_existing_daily_key", lambda r: r.update(ticker="UNKNOWN"), "invalid_existing_daily_key"),
        ("existing_huge_integer_price", lambda r: r.update(first_px=10 ** 400), "invalid_existing_ledger_price"),
    ):
        prior = deepcopy(ledger)
        mutate(prior[0])
        reject_ingest(name, reason, prior=prior)

    old_day = "2026-10-09"
    legacy = CR.events_to_rows([{"ticker": ticker, "kind": "forming", "px": 45.0,
        "ts": old_day + "T02:00:00Z"}], session=old_day)[0]
    legacy["schema"] = CR.FORWARD_SCHEMA
    with_legacy, _ = ingest(prior=[deepcopy(legacy)] + deepcopy(ledger))
    retained_legacy = next(r for r in with_legacy if r["date"] == old_day)
    check("older_valid_legacy_row_unchanged_without_new_provenance", retained_legacy == legacy
          and "ingest_contract" not in retained_legacy)
    target_legacy = deepcopy(legacy)
    target_legacy["date"] = session
    target_legacy["first_ts"] = target_legacy["last_ts"] = session + "T02:00:00Z"
    reject_ingest("target_session_unbound_row_refused", "legacy_unbound_row", prior=[target_legacy])

    parquet_dir = out / "parquet_cases"
    parquet_dir.mkdir(exist_ok=True)

    def guard_parquet(name, frame, reason):
        path = parquet_dir / (name + ".parquet")
        frame.to_parquet(path, index=False)
        before = path.read_bytes()
        writes = []

        def writer(destination, rows):
            writes.append(str(destination))
            RD._write_parquet(destination, rows)

        refusal(name + "_parquet_refuses", lambda: reconcile_file(path,
            read_frame=pd.read_parquet, write_rows=writer,
            reconcile=lambda old: ingest(prior=old)), reason)
        after = path.read_bytes()
        check(name + "_zero_writer_calls_and_bytes_unchanged", not writes and before == after)
        parquet_receipts.append({"case": name, "path": "parquet_cases/" + path.name,
            "input_rows": len(frame), "columns": list(frame.columns), "writer_calls": len(writes),
            "before_sha256": sha256(before).hexdigest(), "after_sha256": sha256(after).hexdigest(),
            "bytes": len(after), "refusal": reason})

    for name, prior in duplicate_cases:
        guard_parquet(name, pd.DataFrame(prior), "duplicate_existing_daily_key")
    guard_parquet("readable_unrelated_table", pd.DataFrame([{"unrelated": "payload"}]),
                  "invalid_existing_ledger_schema")
    wrong_schema = deepcopy(ledger)
    wrong_schema[0]["schema"] = "unrelated/v1"
    guard_parquet("readable_unknown_row_schema", pd.DataFrame(wrong_schema),
                  "invalid_existing_ledger_schema")
    guard_parquet("readable_empty_unknown_table", pd.DataFrame(columns=["unrelated"]),
                  "invalid_existing_ledger_schema")

    legacy_path = parquet_dir / "legacy_compatibility.parquet"
    RD._write_parquet(legacy_path, with_legacy)
    from_file, _ = reconcile_file(legacy_path, read_frame=pd.read_parquet,
        write_rows=RD._write_parquet, reconcile=lambda old: ingest(prior=old))
    old_file_row = next(r for r in from_file if r["date"] == old_day)
    check("older_legacy_parquet_null_columns_do_not_create_provenance",
          all(old_file_row.get(k) == v for k, v in legacy.items())
          and old_file_row.get("ingest_contract") is None
          and old_file_row.get("first_event_id") is None
          and old_file_row.get("quote_contract_id") is None)
    empty_native = parquet_dir / "native_empty.parquet"
    RD._write_parquet(empty_native, [])
    from_empty, _ = reconcile_file(empty_native, read_frame=pd.read_parquet,
        write_rows=RD._write_parquet, reconcile=lambda old: ingest(prior=old))
    check("native_schema_only_empty_ledger_compatible", encoded(from_empty) == encoded(ledger))

    # H3: equal observation time with different membership cannot use key order.
    baseline_close = json.loads(store.objects[latest_key])
    for order in (0, 1):
        left = deepcopy(baseline_close)
        right = deepcopy(baseline_close)
        left["irrelevant_nonce"] = "z" if order else "a"
        right["irrelevant_nonce"] = "a" if order else "z"
        lane = next(k for k, values in right["close_board"]["lanes"].items() if values)
        right["close_board"]["lanes"][lane].pop()
        conflict = deepcopy(store)
        del conflict.objects[latest_key]
        publish(conflict, left)
        publish(conflict, right)
        reject_ingest("equal_time_close_membership_conflict_nonce_order_" + str(order),
                      "conflicting_equal_time_close_evidence", subject=conflict)
    equivalent = deepcopy(baseline_close)
    equivalent["irrelevant_nonce"] = "different envelope metadata"
    equivalent["close_board"]["display_note"] = "different display metadata"
    equivalent["close_board"]["first_close_board_at"] = "metadata cannot order authority"
    for values in equivalent["close_board"]["lanes"].values():
        values.reverse()
    coalesced = deepcopy(store)
    publish(coalesced, equivalent)
    coalesced_rows, coalesced_receipt = ingest(coalesced)
    baseline_rows, baseline_receipt = ingest()
    selected = coalesced_receipt["selected_close_evidence"]
    check("equal_economics_close_coalesces_all_supporting_keys",
          encoded(coalesced_rows) == encoded(baseline_rows)
          and coalesced_receipt["receipt"] == baseline_receipt["receipt"]
          and selected["economics_sha256"] == baseline_receipt["selected_close_evidence"]["economics_sha256"]
          and set(selected["object_keys"]) == {latest_key, spool_key(equivalent, R2)})
    cases.append({"name": "equal_economics_close_coalesces", "expected": "coalesced",
                  **store_delta(coalesced), "selected_close_evidence": selected})

    # H4: every accepted quote is replayed from exact retained source bytes.
    original_quotes = quotes_for(morning)
    one = original_quotes[ticker]
    evidence = one["source_evidence"]
    resolved = quote_resolver.resolve(ticker, evidence, known_by=morning)
    check("source_receipt_hashes_original_utf8_bytes_before_parsing",
          evidence["payload_sha256"] == sha256(evidence["payload_utf8"].encode()).hexdigest()
          and evidence["quote_record_sha256"] == digest(resolved)
          and resolved["source"] == "yahoo"
          and resolved["price_basis"] == "regular"
          and one["price_adjustment"] == "unadjusted_research_fixture")
    spaced_bytes = (" \n" + evidence["payload_utf8"] + "\n ").encode()
    spaced_quotes = quote_resolver.quotes(spaced_bytes, recorded_at=morning)
    check("wire_whitespace_changes_byte_receipt_not_parsed_economics",
          spaced_quotes[ticker]["source_evidence"]["payload_sha256"] == sha256(spaced_bytes).hexdigest()
          and spaced_quotes[ticker]["source_evidence"]["payload_sha256"] != evidence["payload_sha256"]
          and quote_resolver.resolve(ticker, spaced_quotes[ticker]["source_evidence"], known_by=morning) == resolved)
    declarations = (None, "unadjusted_vendor_print", "split_and_dividend_adjusted")
    for basis in declarations:
        natural = deepcopy(original_quotes)
        for q in natural.values():
            q.pop("source_evidence")
            if basis is None:
                q.pop("price_adjustment")
            else:
                q["price_adjustment"] = basis
        art = checked(natural)
        check("unsupported_natural_basis_declaration_" + str(basis), art["events"] == []
              and all(row["state"] == "dark" and row["market_status"] == "unavailable"
                      for row in art["names"].values())
              and set(art["meta"]["quote_rejections"].values()) == {"quote_basis_evidence_unavailable"})
    no_resolver = checked(original_quotes, resolver=None)
    check("caller_cannot_bypass_missing_source_resolver", not no_resolver["events"]
          and set(no_resolver["meta"]["quote_rejections"].values()) == {"quote_basis_evidence_unavailable"})
    for name, change, reason in (
        ("declared_raw_cannot_replace_synthetic_contract", lambda q: q.update(price_adjustment="unadjusted_vendor_print"),
         "unsupported_quote_price_adjustment"),
        ("adjusted_quote_cannot_replace_synthetic_contract", lambda q: q.update(price_adjustment="split_and_dividend_adjusted"),
         "unsupported_quote_price_adjustment"),
        ("copied_quote_price_must_match_payload", lambda q: q.update(price=q["price"] + .01),
         "quote_disagrees_with_source_payload"),
        ("source_payload_bytes_tampered", lambda q: q["source_evidence"].update(payload_utf8=q["source_evidence"]["payload_utf8"] + " "),
         "quote_payload_identity_mismatch"),
        ("unsupported_source_contract", lambda q: q["source_evidence"].update(contract_id="e" * 64),
         "unsupported_quote_source_contract"),
        ("parsed_quote_record_hash_tampered", lambda q: q["source_evidence"].update(quote_record_sha256="e" * 64),
         "quote_record_identity_mismatch"),
        ("source_receipt_future_to_evaluation", lambda q: q["source_evidence"].update(recorded_at=(morning + timedelta(seconds=1)).isoformat()),
         "future_quote_source_receipt"),
    ):
        q = deepcopy(original_quotes)
        change(q[ticker])
        art = checked(q)
        check(name, art["names"][ticker]["reason"] == reason
              and not any(ev["ticker"] == ticker for ev in art["events"]))
    refusal("wrong_native_quote_adapter_identity", lambda: SyntheticQuoteResolver(b"not the pinned adapter"),
            "quote_adapter_source_identity_mismatch")

    # H5: FIRST_WINS must never preserve a tampered copied first observation.
    mutations = {
        "first_px": ledger[0]["first_px"] + 1,
        "cross_px": ledger[0]["cross_px"] + 1,
        "first_ts": (stamp(ledger[0]["first_ts"]) + timedelta(seconds=1)).isoformat(),
        "first_quote_ts": (stamp(ledger[0]["first_quote_ts"]) + timedelta(seconds=1)).isoformat(),
        "quote_payload_sha256": "c" * 64,
        "quote_contract_id": "c" * 64,
        "first_quote_record_sha256": "c" * 64,
        "price_adjustment": "adjusted_invented",
        "cross_basis_close": ledger[0]["cross_basis_close"] + 1,
        "cross_basis_adjustment": "unadjusted_invented",
        "from_state": "invented_previous_state",
        "first_passes": 99,
        "frozen_score_rank": 999,
        "source_board_definition": "invented_definition",
    }
    for field, value in mutations.items():
        prior = deepcopy(ledger)
        prior[0][field] = value
        # Rehashing the copy does not establish authenticity against the spool.
        prior[0]["first_observation_sha256"] = digest(first_observation(prior[0]))
        reject_ingest("tampered_first_observation_" + field,
                      "existing_first_observation_conflict", prior=prior)
    repeat_at = morning + timedelta(minutes=10)
    repeat_q = quotes_for(repeat_at, price_changes={ticker: one["price"] + .0001})
    repeat_art = checked(repeat_q, at=repeat_at)
    repeated = deepcopy(store)
    repeat_doc = envelope(repeat_art, repeat_art["events"], pack)
    publish(repeated, repeat_doc)
    repeated_rows, _ = ingest(repeated, prior=ledger)
    previous = {tuple(r[k] for k in CR.KEY): r for r in ledger}
    changed = [r for r in repeated_rows if r["occurrences"] > previous[tuple(r[k] for k in CR.KEY)]["occurrences"]]
    check("later_authentic_repeat_preserves_first_updates_last_and_count", bool(changed)
          and all(first_observation(r) == first_observation(previous[tuple(r[k] for k in CR.KEY)])
                  and r["first_observation_sha256"] == previous[tuple(r[k] for k in CR.KEY)]["first_observation_sha256"]
                  for r in repeated_rows)
          and all(stamp(r["last_ts"]) == repeat_at
                  and r["occurrences"] == len(r["event_ids"]) for r in changed)
          and next(r for r in changed if r["ticker"] == ticker)["last_px"] == repeat_q[ticker]["price"])
    repeat_again, _ = ingest(repeated, prior=repeated_rows)
    check("later_repeat_replay_idempotent", encoded(repeat_again) == encoded(repeated_rows))
    cases.append({"name": "later_authentic_repeat", "expected": "update_last_preserve_first",
                  **store_delta(repeated), "prior_rows": ledger, "result_rows": repeated_rows})

    # H6-H7: a finite predicate must not throw on a finite JSON integer, and
    # score bounds apply after a pack has been rehashed by its producer.
    huge = 10 ** 400
    check("finite_huge_integer_is_total_and_false", finite(huge) is False)
    huge_quotes = deepcopy(original_quotes)
    huge_quotes[ticker]["price"] = huge
    art = checked(huge_quotes)
    check("huge_quote_is_per_name_refusal_with_other_names_continuing",
          art["names"][ticker]["reason"] == "invalid_quote_price"
          and not any(e["ticker"] == ticker for e in art["events"])
          and any(e["ticker"] != ticker for e in art["events"]))
    refusal("huge_integer_in_source_payload_refuses", lambda: quotes_for(morning, price_changes={ticker: huge}),
            "invalid_quote_payload_price")
    for score in (-1, 100.01, huge):
        invalid = deepcopy(pack)
        invalid["names"][ticker]["frozen"]["score"] = score
        reseal_pack(invalid)
        refusal("rehashed_pack_invalid_score_" + ("huge" if score == huge else str(score)),
                lambda p=invalid: validate_pack(p), "invalid_frozen_score")
    for score in (0, 100):
        boundary = deepcopy(pack)
        boundary["names"][ticker]["frozen"]["score"] = score
        reseal_pack(boundary)
        validate_pack(boundary)
        check("pack_score_boundary_" + str(score), True)

    # Draft-review amendments: receipt/pack knowledge is bounded by the event,
    # not a later publishing envelope. The positive control is actually native.
    later = morning + timedelta(minutes=1)
    later_art = checked(quotes_for(later, quote_at=morning), at=later)
    later_doc = envelope(later_art, later_art["events"], pack)

    def only_spool(doc, p=pack):
        subject = deepcopy(store)
        for key in event_keys:
            del subject.objects[key]
        subject.objects[pack_key(p, R2)] = encoded(p)
        publish(subject, doc)
        return subject

    fractional_at = morning + timedelta(microseconds=500000)
    fractional_art = checked(quotes_for(fractional_at), at=fractional_at)
    fractional_doc = envelope(fractional_art, fractional_art["events"], pack)
    fractional_store = only_spool(fractional_doc)
    fractional_rows, _ = ingest(fractional_store)
    check("native_fractional_event_time_preserves_source_knowledge_boundary",
          bool(fractional_rows) and stamp(fractional_doc["built_at"]) == fractional_at
          and all(stamp(r["first_ts"]) == fractional_at for r in fractional_rows))
    cases.append({"name": "native_fractional_event_time", "expected": "precise_event_time",
                  **store_delta(fractional_store), "prior_rows": None,
                  "result_rows": fractional_rows})

    timely = only_spool(later_doc)
    timely_rows, _ = ingest(timely)
    check("native_source_receipt_and_pack_known_by_event_control", bool(timely_rows)
          and all(stamp(r["first_ts"]) == later for r in timely_rows))
    backdated = deepcopy(later_doc)
    for ev in backdated["events"]:
        ev["ts"] = morning.isoformat()
        reseal_event(ev, pack["pack_id"])
    reject_ingest("backdated_event_before_source_receipt_refuses", "future_quote_source_receipt",
                  subject=only_spool(backdated))
    future_pack = deepcopy(pack)
    future_pack["built_at"] = later.isoformat()
    reseal_pack(future_pack)
    original_art = checked(original_quotes)
    too_early = envelope(original_art, original_art["events"], future_pack)
    too_early["built_at"] = later.isoformat()
    for ev in too_early["events"]:
        reseal_event(ev, future_pack["pack_id"])
    reject_ingest("backdated_event_before_pack_build_refuses", "future_pack_build",
                  subject=only_spool(too_early, future_pack))

    # Equal-second prices and equal-second source-byte differences are both
    # unorderable. An exact event-ID duplicate has a separate positive baseline.
    for name, q in (
        ("same_event_time_conflicting_price_refuses", quotes_for(morning,
             price_changes={ticker: one["price"] + .0001})),
        ("same_event_time_distinct_source_receipt_refuses", spaced_quotes),
    ):
        simultaneous = checked(q)
        doc = envelope(simultaneous, simultaneous["events"], pack)
        subject = deepcopy(store)
        publish(subject, doc)
        reject_ingest(name, "ambiguous_equal_time_events", subject=subject)

    exact_cases = {"schema": "cn-integration-repair-cases/v1",
        "SYNTHETIC_RESEARCH_ONLY": True,
        "base": "integration_fixture.json plus its archived base and settlement packs",
        "prior_rows_null_means_empty": True,
        "canonical": "synthetic_settlement_board.json.gz",
        "cases": cases}
    (out / "repair_cases.json").write_bytes(encoded(exact_cases) + b"\n")
    (out / "parquet_receipts.json").write_bytes(encoded({"schema": "cn-integration-parquet-repair/v1",
        "runtime": "actual pandas/Parquet, native atomic writer injected, no mocked read/write engine",
        "cases": parquet_receipts}) + b"\n")
    return {"retained_store_and_prior_cases": len(cases),
            "retained_cases_path": "repair_cases.json",
            "real_parquet_refusal_cases": parquet_receipts,
            "first_observation_fields": list(FIRST_OBSERVATION_FIELDS),
            "quote_contract_id": quote_resolver.contract_id,
            "natural_provider_adjustment_qualification": "unavailable",
            "same_timestamp_event_policy": "exact identity deduplication; distinct identities refused",
            "timing_policy": "pack and source receipt known by event time, event known by envelope time"}
