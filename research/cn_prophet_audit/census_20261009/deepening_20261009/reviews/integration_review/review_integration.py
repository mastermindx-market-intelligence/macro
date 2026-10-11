#!/usr/bin/env python3
"""Independent hostile review of the stable offline integration proposal.

Executes the unchanged prototype and a bounded bundle of exact Git-pinned native
functions. All object I/O is memory-only and Parquet writes stay beside this
review. No completed lab, source worktree, vendor, or production store is touched.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
import json
import socket
import sys

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
DOCKET = OUT.parents[2]
LAB = DOCKET / "deepening_20261009/integration_lab"
PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"
MANIFEST_SHA = "d755a012d80469c241a554252e61bee88e604eb445ce7ca03ec1e2eecfdbc8b6"
SESSION = "2026-10-12"
NOW = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)
CHECKS = []


def read(path):
    return json.loads(path.read_text())


def hash_file(path):
    return sha256(path.read_bytes()).hexdigest()


def check(name, condition):
    CHECKS.append({"name": name, "status": "PASS" if condition else "FAIL"})
    if not condition:
        raise AssertionError(name)


def no_network(*args, **kwargs):
    raise RuntimeError("Network is disabled in this independent offline review")


def capture(fn):
    try:
        value = fn()
        return {"outcome": "accepted", "value": value}
    except Exception as exc:
        return {"outcome": "exception", "exception_class": type(exc).__name__,
                "reason": getattr(exc, "reason", str(exc))}


def main():
    check("stable_manifest_hash", hash_file(LAB / "INTEGRATION_MANIFEST.json") == MANIFEST_SHA)
    manifest = read(LAB / "INTEGRATION_MANIFEST.json")
    original_hashes = {"INTEGRATION_MANIFEST.json": MANIFEST_SHA}
    for item in manifest["files"]:
        check("original_file:" + item["path"], hash_file(LAB / item["path"]) == item["sha256"])
        original_hashes[item["path"]] = item["sha256"]
    retained_results = read(LAB / "integration_results.json")
    fixture = read(LAB / "integration_fixture.json")
    bundle = read(OUT / "native_source_bundle.json")
    check("source_pin", bundle["source_sha"] == manifest["study_source_sha"] == PIN)
    for path, data in bundle["files"].items():
        check("native_source:" + path, sha256(data["code"].encode()).hexdigest()
              == data["sha256"] == retained_results["source_manifest"][path]["sha256"])

    # In-memory packages prevent imports from a shared checkout. The code is
    # compiled unchanged; native function bodies are not reimplemented here.
    for name in ("lib", "engine", "engine.prophet_live", "scripts"):
        module = ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
        if "." in name:
            parent, child = name.rsplit(".", 1)
            setattr(sys.modules[parent], child, module)
    modules = {}
    load_order = ["lib/exchange_holidays.py", "lib/cn_calendar.py",
                  "engine/prophet_live/interval.py", "engine/prophet_live/live_states.py",
                  "engine/prophet_live/cn_clock.py", "engine/prophet_live/cn_states.py",
                  "engine/prophet_live/cn_reconcile.py", "engine/prophet_live/r2io.py",
                  "scripts/reconcile_cn_live.py"]
    for path in load_order:
        name = path[:-3].replace("/", ".")
        module = ModuleType(name)
        module.__file__ = str(OUT / "_virtual_pinned_source" / path)
        module.__package__ = name.rsplit(".", 1)[0]
        sys.modules[name] = module
        parent, child = name.rsplit(".", 1)
        setattr(sys.modules[parent], child, module)
        exec(compile(bundle["files"][path]["code"], module.__file__, "exec"), module.__dict__)
        modules[path] = module
    subject = ModuleType("integration_contract_under_review")
    subject.__file__ = str(LAB / "contract_prototype.py")
    exec(compile((LAB / "contract_prototype.py").read_text(), subject.__file__, "exec"), subject.__dict__)
    B = subject
    CR = modules["engine/prophet_live/cn_reconcile.py"]
    R2 = modules["engine/prophet_live/r2io.py"]
    LS = modules["engine/prophet_live/live_states.py"]
    CS = modules["engine/prophet_live/cn_states.py"]
    clock = modules["engine/prophet_live/cn_clock.py"]
    calendar = modules["lib/cn_calendar.py"]
    RD = modules["scripts/reconcile_cn_live.py"]
    base_pack, settlement = fixture["base_pack"], fixture["settlement_pack"]
    B.validate_pack(base_pack)
    B.validate_pack(settlement)

    def fresh_store():
        store = B.MemoryR2(page_size=2)
        for key, envelope in fixture["events"].items():
            store.put(key, envelope)
        store.put(B.pack_key(base_pack, R2), base_pack)
        store.put(B.pack_key(settlement, R2), settlement)
        store.put(R2.CN_PACK_KEY, settlement)
        return store

    def ingest(store=None, *, prior=None, settle=settlement, canonical=None):
        return B.consume(store if store is not None else fresh_store(), R2, CR, clock, calendar, LS,
                         session=SESSION, now=NOW, existing=[] if prior is None else prior,
                         settlement_pack=settle, canonical_board=canonical,
                         canonical_board_raw=B.encoded(canonical) if canonical is not None else None)

    baseline, baseline_receipt = ingest()
    check("retained_ledger_reproduces_with_native_functions", B.encoded(baseline) == B.encoded(fixture["ledger"]))
    replay, _ = ingest(prior=baseline)
    check("positive_replay_idempotence", B.encoded(replay) == B.encoded(baseline))
    check("positive_prior_generation_survives_rollover", base_pack["pack_id"] != settlement["pack_id"]
          and all(row["first_pack_id"] == base_pack["pack_id"] for row in baseline))

    # F1: delete whole immutable transition objects, leaving the close evidence
    # present. The remaining objects keep their genuine original content hashes.
    event_keys = [key for key, doc in fixture["events"].items() if doc["events"]]
    first_key = min(event_keys)
    omission_cases = []
    for label, omitted_keys in [("first_transition_object", [first_key]),
                                ("all_transition_objects", event_keys)]:
        store = fresh_store()
        for key in omitted_keys:
            del store.objects[key]
        replayed, receipt = ingest(store, prior=baseline)
        omitted_events = [ev for key in omitted_keys for ev in fixture["events"][key]["events"]]
        check("omission_accepted:" + label, B.encoded(replayed) == B.encoded(baseline))
        omission_cases.append({"variant": label, "omitted_object_keys": omitted_keys,
                               "omitted_event_ids": [e["event_id"] for e in omitted_events],
                               "omitted_daily_keys": [[SESSION, e["ticker"], e["kind"]] for e in omitted_events],
                               "returned_rows": len(replayed), "returned_distinct_events": receipt["distinct_events"],
                               "returned_spool_objects": receipt["spool_objects"], "refused": False})
    partial_old = deepcopy(baseline)
    partial_old[0]["event_ids"].append("a" * 64)
    partial_guard = capture(lambda: ingest(prior=partial_old))
    check("positive_partial_regression_guard_exists", partial_guard.get("reason") == "spool_regression")

    # F2: keep the conflicting close contents/time/generation fixed. Vary only
    # inert envelope metadata until its digest sorts either side of the other.
    latest_doc = deepcopy(max((d for d in fixture["events"].values() if d["close_board"]),
                              key=lambda d: d["built_at"]))
    dropped_ticker = "603799.SS"
    alternate = deepcopy(latest_doc)
    for lane in alternate["close_board"]["lanes"].values():
        lane[:] = [row for row in lane if row["ticker"] != dropped_ticker]
    canonical = {"as_of": SESSION, "board_definition": "cn_prophet_v4",
                 "research_fixture": "SYNTHETIC_INDEPENDENT_CLOSE_CONFLICT_REVIEW",
                 "buy": [{"ticker": "002460.SZ"}], "more_actionable": [],
                 "forming": [{"ticker": "300750.SZ"}]}
    tied_settlement = deepcopy(settlement)
    tied_settlement["source_board"]["artifact_sha256"] = sha256(B.encoded(canonical)).hexdigest()
    tied_settlement.pop("pack_id")
    tied_settlement["pack_id"] = B.digest(tied_settlement)
    B.validate_pack(tied_settlement)
    fixed_key = B.spool_key(latest_doc, R2)
    variants = {}
    for nonce in range(1024):
        candidate = deepcopy(alternate)
        candidate["review_nonce"] = nonce
        key = B.spool_key(candidate, R2)
        relation = "before" if key < fixed_key else "after"
        variants.setdefault(relation, (key, candidate))
        if len(variants) == 2:
            break
    check("bounded_digest_order_counterexamples_found", len(variants) == 2)
    close_cases = []
    for relation in ("before", "after"):
        alternate_key, alternate_doc = variants[relation]
        store = fresh_store()
        for key, doc in fixture["events"].items():
            if doc["close_board"]:
                del store.objects[key]
        store.put(fixed_key, latest_doc)
        store.put(alternate_key, alternate_doc)
        rows, receipt = ingest(store, settle=tied_settlement, canonical=canonical)
        actual = receipt["receipt"]
        expected_close = alternate_doc["close_board"] if relation == "before" else latest_doc["close_board"]
        check("close_tie_follows_object_key:" + relation,
              actual == CR.confirmation_receipt(expected_close, canonical, session=SESSION, built_at=NOW))
        close_cases.append({"alternate_key_sorts": relation, "fixed_object_key": fixed_key,
                            "alternate_object_key": alternate_key,
                            "fixed_close_content_sha256": B.digest(latest_doc["close_board"]),
                            "alternate_close_content_sha256": B.digest(alternate_doc["close_board"]),
                            "built_at": latest_doc["built_at"], "pack_id": latest_doc["pack_id"],
                            "inert_review_nonce": alternate_doc["review_nonce"],
                            "receipt": actual, "returned_rows": len(rows), "refused": False})
    check("close_tie_receipt_changes_without_time_membership_or_generation_change",
          close_cases[0]["receipt"]["n_dropped"] == 0 and close_cases[1]["receipt"]["n_dropped"] == 1
          and close_cases[0]["alternate_close_content_sha256"] == close_cases[1]["alternate_close_content_sha256"])

    # F3: same numeric quotes/clock, three different supplied basis declarations.
    # The native evaluator and proposal run unchanged, and the resulting event
    # is consumed by native reconciliation, not merely inspected in a test stub.
    morning = datetime(2026, 10, 12, 2, tzinfo=timezone.utc)
    prices = {ev["ticker"]: ev["price"] for ev in fixture["events"][first_key]["events"]}
    cfg = LS.live_cfg({"live": {"delayed_min": 0}})

    def quotes(adjustment):
        result = {ticker: {"price": prices[ticker], "prev_close": entry["as_of_close"],
                           "quote_ts": morning.isoformat().replace("+00:00", "Z"),
                           "price_basis": "regular", "source": "SYNTHETIC_INDEPENDENT_REVIEW"}
                  for ticker, entry in base_pack["names"].items()}
        if adjustment is not None:
            for quote in result.values():
                quote["price_adjustment"] = adjustment
        return result

    price_cases = []
    for adjustment in (None, "split_and_dividend_adjusted", "unadjusted_vendor_print"):
        input_quotes = quotes(adjustment)
        artifact = B.evaluate_checked(CS.evaluate, LS, clock, base_pack, input_quotes, None,
                                      now=morning, cfg=cfg, delay_min=0)
        check("native_provenance_probe_has_events:" + str(adjustment), len(artifact["events"]) == 3)
        store = fresh_store()
        for key in fixture["events"]:
            del store.objects[key]
        doc = B.envelope(artifact, artifact["events"], base_pack)
        store.put(B.spool_key(doc, R2), doc)
        rows, receipt = ingest(store)
        check("source_adjustment_overstamped:" + str(adjustment),
              all(e["price_adjustment"] == "unadjusted_vendor_print" for e in artifact["events"])
              and all(r["price_adjustment"] == "unadjusted_vendor_print" for r in rows))
        price_cases.append({"input_price_adjustment": adjustment,
                            "input_price_basis": "regular",
                            "output_event_price_adjustments": sorted({e["price_adjustment"] for e in artifact["events"]}),
                            "event_ids": [e["event_id"] for e in artifact["events"]],
                            "ledger_price_adjustments": sorted({r["price_adjustment"] for r in rows}),
                            "ledger_rows": len(rows), "quote_rejections": artifact["meta"]["quote_rejections"],
                            "refused": False})
    check("distinct_source_adjustment_declarations_collapse_to_same_event_identity",
          price_cases[0]["event_ids"] == price_cases[1]["event_ids"] == price_cases[2]["event_ids"])

    # F4: valid Parquet, duplicate daily key, previously retained event identity.
    # Native merge and the proposed full file path run against an actual file.
    import pandas as pd
    parquet_dir = OUT / "parquet_cases"
    parquet_dir.mkdir(exist_ok=True)
    duplicate = deepcopy(baseline[0])
    sentinel_event_id = "d" * 64
    duplicate["event_ids"].append(sentinel_event_id)
    duplicate["occurrences"] += 1
    duplicate["last_ts"] = "2026-10-12T02:01:00Z"
    prior_duplicate_rows = deepcopy(baseline) + [duplicate]
    path = parquet_dir / "duplicate_daily_keys.parquet"
    try:
        pd.io.parquet.get_engine("auto")
        parquet_available = True
    except ImportError:
        parquet_available = False
    if parquet_available:
        pd.DataFrame(prior_duplicate_rows).to_parquet(path, index=False)
        before = path.read_bytes()
        (parquet_dir / "duplicate_daily_keys.before.parquet").write_bytes(before)
        check("duplicate_input_is_readable_parquet", len(pd.read_parquet(path)) == 5)
        write_calls = []

        def real_writer(dest, rows):
            write_calls.append({"path": str(dest.relative_to(OUT)), "row_n": len(rows)})
            RD._write_parquet(dest, rows)

        rewritten, _ = B.reconcile_file(path, read_frame=pd.read_parquet,
            write_rows=real_writer, reconcile=lambda old: ingest(prior=old))
        disk_after = pd.read_parquet(path)
        retained_event_ids = {identity for row in rewritten for identity in row["event_ids"]}
        check("duplicate_key_extra_history_is_silently_removed",
              len(rewritten) == len(disk_after) == 4 and sentinel_event_id not in retained_event_ids
              and len(write_calls) == 1)
        duplicate_evidence = {"input_row_n": 5, "output_row_n": len(rewritten),
            "lost_event_id": sentinel_event_id, "lost_event_present_after_write": False,
            "before_sha256": sha256(before).hexdigest(), "after_sha256": hash_file(path),
            "writer_calls": write_calls, "execution_origin": "native_write_in_this_process"}
    else:
        # The chat runtime has pandas but no Parquet engine. The separately
        # executed helper uses the installed host engine and exact same subject
        # and fixture hashes. Retain and verify its receipt and actual files;
        # do not represent this branch as a local native Parquet execution.
        receipt_path = OUT / "parquet_review_receipt.json"
        check("recorded_native_parquet_receipt_hash", hash_file(receipt_path)
              == "a70ad278ac1abddd6f27841da68fe50830b1219940f1fc0ccc9ef6075df6d0a9")
        host_receipt = read(receipt_path)
        check("recorded_parquet_helper_hash", host_receipt["script_sha256"]
              == hash_file(OUT / "parquet_counterexample.py"))
        check("recorded_parquet_subject_and_fixture", host_receipt["subject_inputs_sha256"]["contract_prototype.py"]
              == original_hashes["contract_prototype.py"]
              and host_receipt["subject_inputs_sha256"]["results/integration_fixture.json"]
              == original_hashes["integration_fixture.json"])
        check("recorded_parquet_native_sources", all(digest == bundle["files"][name]["sha256"]
              for name, digest in host_receipt["native_source_sha256"].items()))
        check("recorded_parquet_input_bytes", hash_file(parquet_dir / "duplicate_daily_keys.before.parquet")
              == host_receipt["evidence"]["before_sha256"])
        check("recorded_parquet_output_bytes", hash_file(path) == host_receipt["evidence"]["after_sha256"])
        duplicate_evidence = {**host_receipt["evidence"],
            "execution_origin": "independent_host_native_write_receipt_and_binary_files",
            "receipt_sha256": hash_file(receipt_path), "host_execution": host_receipt["execution"]}
        check("recorded_native_parquet_loss", duplicate_evidence["input_row_n"] == 5
              and duplicate_evidence["output_row_n"] == 4
              and duplicate_evidence["lost_event_present_after_write"] is False
              and duplicate_evidence["native_writer_row_counts"] == [4])
    reverse_order = capture(lambda: ingest(prior=[duplicate] + deepcopy(baseline)))
    check("duplicate_order_changes_refusal", reverse_order.get("reason") == "spool_regression")
    duplicate_evidence["reversed_duplicate_order"] = reverse_order

    # F5/F6: standalone archived-pack validation and huge JSON integer behavior.
    score_cases = []
    for value in (-1, 100.01):
        pack = deepcopy(base_pack)
        pack["names"]["002460.SZ"]["frozen"]["score"] = value
        pack.pop("pack_id")
        pack["pack_id"] = B.digest(pack)
        got = capture(lambda p=pack: B.validate_pack(p))
        check("out_of_range_standalone_score_accepted:" + str(value), got["outcome"] == "accepted")
        score_cases.append({"score": value, "correctly_recomputed_pack_id": pack["pack_id"],
                            "outcome": got["outcome"]})
    huge = 10 ** 400
    finite_result = capture(lambda: B.finite(huge, positive=True))
    huge_quotes = quotes("unadjusted_vendor_print")
    huge_quotes["002460.SZ"]["price"] = huge
    huge_evaluation = capture(lambda: B.evaluate_checked(CS.evaluate, LS, clock, base_pack,
                             huge_quotes, None, now=morning, cfg=cfg, delay_min=0))
    check("huge_integer_breaks_boolean_numeric_predicate", finite_result.get("exception_class") == "OverflowError")
    check("huge_integer_escapes_per_name_refusal", huge_evaluation.get("exception_class") == "OverflowError")

    # F7: an unchanged event hash is not proof its denormalized immutable columns
    # still agree. FIRST_WINS retains this wrong value while identity checks pass.
    inconsistent = deepcopy(baseline)
    original_price = inconsistent[0]["first_px"]
    inconsistent[0]["first_px"] = original_price + 1.0
    price_replayed, _ = ingest(prior=inconsistent)
    target = next(r for r in price_replayed if all(r[k] == inconsistent[0][k] for k in CR.KEY))
    source_event = next(e for d in fixture["events"].values() for e in d["events"]
                        if e["event_id"] == target["first_event_id"])
    check("same_event_identity_can_retain_inconsistent_first_price",
          target["first_event_id"] == baseline[0]["first_event_id"]
          and target["first_px"] == original_price + 1.0 and target["first_px"] != source_event["price"])

    for name, expected in original_hashes.items():
        check("unchanged_completed_lab:" + name, hash_file(LAB / name) == expected)
    findings = [
        {"id": "F1", "severity": "high", "status": "CONFIRMED", "title": "Whole-key spool omission evades regression detection",
         "evidence": omission_cases, "positive_control": partial_guard,
         "required_behavior": "Before reconstructing/merging rows, compare the union of previously consumed event IDs for every existing row in the requested session with all currently resolved spool IDs. Refuse any unexplained missing key or event; only an explicit adjudicated retention/correction contract may waive it."},
        {"id": "F2", "severity": "high", "status": "CONFIRMED", "title": "Conflicting equal-time close snapshots use digest ordering as authority",
         "evidence": close_cases,
         "required_behavior": "Group close evidence by source generation and observation/pass identity. Coalesce identical evidence, refuse conflicting evidence at equal authority, and retain the exact selected close object ID in the receipt. Do not let unrelated metadata hashes choose membership truth."},
        {"id": "F3", "severity": "high", "status": "CONFIRMED", "title": "Source quote adjustment is replaced by an unsupported raw declaration",
         "evidence": price_cases,
         "required_behavior": "Require and validate an adapter/provider price-basis declaration with provenance; preserve its supplied identity. A missing or incompatible adjustment must remain unavailable or be refused. A previous-close numerical match is not proof of an unadjusted basis."},
        {"id": "F4", "severity": "high", "status": "CONFIRMED", "title": "Readable duplicate-key Parquet silently loses retained history",
         "evidence": duplicate_evidence,
         "required_behavior": "Validate existing daily-key uniqueness and key/schema integrity before native merge. Refuse conflicting duplicates before any write and preserve the original bytes; a separately specified exact-duplicate normalization can be considered without silently discarding evidence."},
        {"id": "F5", "severity": "medium", "status": "CONFIRMED", "title": "Standalone archived-pack validator omits the frozen score range",
         "evidence": score_cases,
         "required_behavior": "Apply the same measured 0-to-100 score domain at the standalone pack trust boundary, not only when loading a canonical board."},
        {"id": "F6", "severity": "medium", "status": "CONFIRMED", "title": "Huge finite JSON integer crashes the numeric validator",
         "evidence": {"integer_decimal_digits": 401, "finite_predicate": finite_result, "one_bad_quote_evaluation": huge_evaluation},
         "required_behavior": "Make numeric-domain validation total over JSON values. Reject out-of-domain magnitudes without conversion overflow and preserve the intended per-name refusal or typed ingest refusal channel."},
        {"id": "F7", "severity": "high", "status": "CONFIRMED", "title": "First-event identity can coexist with a conflicting stored first price",
         "evidence": {"daily_key": [target[k] for k in CR.KEY], "first_event_id": target["first_event_id"],
                      "source_event_price": source_event["price"], "stored_first_price_before_replay": inconsistent[0]["first_px"],
                      "returned_first_price": target["first_px"], "refused": False},
         "required_behavior": "Bind and compare every immutable denormalized first-observation field with the resolved first event/pack, or validate a canonical first-observation record digest. Refuse discrepancies; do not silently preserve or repair them."},
    ]
    result = {"schema": "cn_integration_independent_adversarial_review_v1", "study_source_sha": PIN,
              "status": "BLOCKED_FOR_END_TO_END_IMPLEMENTATION_AS_WRITTEN", "reviewed_manifest_sha256": MANIFEST_SHA,
              "review_script_sha256": hash_file(Path(__file__)),
              "native_source_bundle_sha256": hash_file(OUT / "native_source_bundle.json"),
              "original_input_sha256": original_hashes,
              "native_source_sha256": {path: item["sha256"] for path, item in bundle["files"].items()},
              "positive_baseline": {"ledger_rows": len(baseline), "distinct_events": baseline_receipt["distinct_events"],
                                    "exact_retained_ledger_reproduced": True, "idempotent_replay": True,
                                    "prior_pack_id": base_pack["pack_id"], "settlement_pack_id": settlement["pack_id"]},
              "findings": findings,
              "limits": ["The actual unmodified native functions and unchanged proposal execute on retained or explicitly mutated synthetic fixtures.",
                         "The compact canonical board in the equal-time conflict case is a newly labeled synthetic fixture, with its hash deliberately bound into a new synthetic settlement generation.",
                         "No claim that the reproduced bad inputs occurred naturally in production, or that historical ledger data was actually lost.",
                         "The first-object omission leaves ledger rows intact but falsely treats missing spool evidence as successful reconciliation.",
                         "The duplicate-key counterexample performs a real native atomic write only to a review-owned temporary Parquet path.",
                         "The three-join architecture remains useful; the reported 63 checks do not establish the stronger completeness, immutability, or provenance claims against these counterexamples."],
              "safety": {"production_effects": False, "vendor_calls": False, "credential_reads": False,
                         "network_disabled_during_execution": True, "completed_labs_changed": False,
                         "object_store": "memory", "parquet_write_scope": "this review directory only"},
              "verification": {"passed_checks": len(CHECKS), "failed_checks": 0, "findings_confirmed": len(findings),
                               "python": sys.version, "pandas": pd.__version__,
                               "local_parquet_engine_available": parquet_available,
                               "parquet_execution_origin": duplicate_evidence["execution_origin"]}, "checks": CHECKS}
    destination = OUT / "REVIEW_RESULTS.json"
    destination.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "confirmed_findings": len(findings), "checks": len(CHECKS),
                      "result_sha256": hash_file(destination)}, sort_keys=True))


if __name__ == "__main__":
    with patch.object(socket.socket, "connect", no_network), patch.object(socket, "create_connection", no_network):
        main()
