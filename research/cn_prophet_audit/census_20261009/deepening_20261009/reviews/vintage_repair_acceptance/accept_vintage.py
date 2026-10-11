#!/usr/bin/env python3
"""Independent bounded acceptance of the sealed coupled vintage contract.

The implementation under review is never edited. All fixtures, replay output
and this review's results are written only beside this script.
"""
from __future__ import annotations
import ast
from collections import Counter
import contextlib
import copy
import hashlib
import io
import json
import logging
import math
from pathlib import Path
import shutil
import sys
from types import ModuleType
import pandas as pd

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAPSHOT = HERE / "reviewed_candidate"
EXPECTED_MANIFEST = "2ec4ad61150efa1ad01b10137ed3d1a0070ba6412770edc2f4e79a098945eec5"
EXPECTED_CONTRACT = "ea8c3d3da6b3d064563f64e3f78b6e4590530fc51bbe92535cf2cce7e1c2bdef"


def sha(raw): return hashlib.sha256(raw).hexdigest()


def encode(value):
    # Independent stdlib fixture serialization. The bytes themselves are the
    # source object; no producer fixture constructor is reused here.
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sealed(body):
    return {**copy.deepcopy(body), "event_id": sha(encode(body))}


def main():
    mraw = (SNAPSHOT / "MANIFEST.json").read_bytes()
    assert sha(mraw) == EXPECTED_MANIFEST
    manifest = json.loads(mraw)
    for rel, identity in manifest["files"].items():
        b = (SNAPSHOT / rel).read_bytes()
        assert len(b) == identity["bytes"] and sha(b) == identity["sha256"], rel
    assert sha((SNAPSHOT / "contract.py").read_bytes()) == EXPECTED_CONTRACT
    freeze = json.loads((HERE / "INPUT_FREEZE.json").read_bytes())
    for rel, identity in freeze["read_only_external_inputs"].items():
        b = (ROOT / rel).read_bytes()
        assert len(b) == identity["bytes"] and sha(b) == identity["sha256"], rel

    checks, witnesses, findings = [], {}, {}
    def check(name, condition, details=None, finding=None, family="interface"):
        row = {"name": name, "passed": bool(condition), "family": family, "details": details}
        if finding:
            row["finding"] = finding
            findings[finding] = "CLOSED" if condition else "OPEN"
        checks.append(row)
        return row

    previous = {name: sys.modules.get(name) for name in ["contract", "retention", "shape"]}
    def load(path, name, register=False):
        module = ModuleType(name); module.__file__ = str(path)
        if register: sys.modules[name] = module
        exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
        return module

    try:
        C = load(SNAPSHOT / "contract.py", "contract", True)
        R = load(SNAPSHOT / "retention.py", "retention", True)
        S = load(SNAPSHOT / "shape.py", "shape", True)
        replay = HERE / "producer_replay"; replay.mkdir(exist_ok=True)
        for name in ["contract.py", "retention.py", "shape.py", "verify.py"]:
            shutil.copyfile(SNAPSHOT / name, replay / name)
        producer = load(replay / "verify.py", "independently_replayed_vintage_producer")
        # This redirects only input/output paths, not test or contract logic.
        producer.ROOT = ROOT
        producer.HERE = replay
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            producer.main()
        (replay / "execution.log").write_text(captured.getvalue())
        pr = json.loads((replay / "results.json").read_bytes())
        check("sealed_producer_104_checks_reproduced", pr["status"] == "PASS" and pr["test_count"] == 104,
              {"test_count": pr["test_count"], "families": pr["families"], "stdout": captured.getvalue().strip()}, family="producer_reproduction")
        check("sealed_producer_result_byte_identity", (replay/"results.json").read_bytes() == (SNAPSHOT/"results.json").read_bytes(),
              {"sha256": sha((replay/"results.json").read_bytes())}, family="producer_reproduction")
        check("sealed_producer_fixture_byte_identity", (replay/"fixtures.json").read_bytes() == (SNAPSHOT/"fixtures.json").read_bytes(),
              {"sha256": sha((replay/"fixtures.json").read_bytes())}, family="producer_reproduction")

        def refuse(name, operation, expected, *, finding=None, family="interface", details=None):
            allowed = {expected} if isinstance(expected, str) else set(expected)
            try:
                result = operation()
            except C.EvidenceError as exc:
                outcome = {"outcome": "REFUSED", "reason": str(exc)}
                okay = str(exc) in allowed
            except Exception as exc:
                outcome = {"outcome": "UNTYPED_EXCEPTION", "exception": type(exc).__name__, "reason": str(exc)}
                okay = False
            else:
                outcome = {"outcome": "ADMITTED", "result": result}
                okay = False
            check(name, okay, {"expected": sorted(allowed), **outcome, "input_note": details}, finding, family)

        sessions = {day: {"session_open": day + "T09:30:00+08:00", "session_close": day + "T15:00:00+08:00"}
                    for day in ["2026-09-16", "2026-09-17", "2026-09-29", "2026-09-30", "2026-10-12"]}
        calendar = C.CalendarFixture(sessions)
        blobs = {}
        def put_raw(raw):
            key = sha(raw); blobs[key] = raw; return key
        def put(ticker, rows, **changes):
            source = {"schema": "research.price_fixture.v2", "fixture_only": True, "ticker": ticker,
                      "provider_id": "INDEPENDENT_SYNTHETIC_FIXTURE", "basis_id": "DECLARED_SYNTHETIC_" + ticker,
                      "price_adjustment": "unadjusted", "clock_kind": "producer_available_at",
                      "available_at": "2026-09-30T08:00:00Z",
                      "rows": [{"session": d, "bar": copy.deepcopy(b)} for d,b in rows.items()]}
            source.update(changes)
            return put_raw(encode(source))
        stock_rows = {"2026-09-16": {"open": 100, "high": 105, "low": 99, "close": 103, "volume": 17},
                      "2026-09-17": {"open": 107, "high": 109, "low": 106, "close": 108, "volume": 19},
                      "2026-09-29": {"open": 119, "high": 122, "low": 118, "close": 121, "volume": 23}}
        bench_rows = {"2026-09-16": {"open": 200, "high": 205, "low": 199, "close": 204},
                      "2026-09-29": {"open": 218, "high": 221, "low": 217, "close": 220}}
        sk = put("000001.SZ", stock_rows); bk = put("510300.SS", bench_rows)
        def mark(key=sk, ticker="000001.SZ", session="2026-09-16", anchor="session_open", **options):
            return C.mark_from_source(ticker=ticker, session=session, anchor=anchor, source_sha256=key,
                                      resolve_source=options.pop("resolve_source", blobs.__getitem__),
                                      calendar=options.pop("calendar", calendar), **options)
        se = mark(); sx = mark(session="2026-09-29", anchor="session_close")
        be = mark(bk, "510300.SS"); bx = mark(bk, "510300.SS", "2026-09-29", "session_close")
        def compare(a=se, b=sx, c=be, d=bx, **changes):
            options = {"published_at": "2026-09-15T08:00:00Z", "graded_at": "2026-10-09T08:00:00Z",
                       "resolve_source": blobs.__getitem__, "calendar": calendar}
            options.update(changes)
            return C.aligned_excess(a, b, c, d, **options)
        expected_excess = ((121/100-1)-(220/200-1))*100
        result = compare()
        check("independent_distinct_row_field_positive_arithmetic", math.isclose(result["excess_pp"], expected_excess, abs_tol=1e-12)
              and result["status"] == "ALIGNED_MARK_DIAGNOSTIC" and result["execution_status"] == "MARK_ONLY", result)
        roundtrip = [json.loads(encode(m)) for m in [se,sx,be,bx]]
        check("serialized_valid_marks_revalidate", compare(*roundtrip) == result)
        check("at_entry_publication_and_at_source_grading_boundaries", compare(published_at="2026-09-16T09:30:00+08:00", graded_at="2026-09-30T08:00:00Z") == result)

        # V1: original semantic variants are adapted to the stricter repaired
        # source/ticker interface, so incidental invalid identities do not mask
        # the temporal responsibility under challenge.
        future_early = put("000001.SZ", {"2026-10-12": {"close": 130}}, available_at="2026-10-09T08:00:00Z")
        refuse("V1.1 future finalized exit with earlier availability", lambda: mark(future_early, session="2026-10-12", anchor="session_close"),
               "SOURCE_PRECEDES_FINALIZED_BAR", finding="V1.1")
        refuse("V1.2 unrelated later free entry clock", lambda: compare(published_at="2026-10-01T08:00:00Z", entry_anchor_at="2026-10-02T01:30:00Z"),
               "ENTRY_CLOCK_BINDING_MISMATCH", finding="V1.2")
        refuse("V1.3 impossible calendar date", lambda: mark(session="2026-09-31"), "SESSION_INVALID", finding="V1.3")
        future_real = put("000001.SZ", {**stock_rows, "2026-10-12": {"close": 130}}, available_at="2026-10-12T08:00:00Z")
        future_mark = mark(future_real, session="2026-10-12", anchor="session_close")
        refuse("honestly late exit still cannot grade before exit anchor", lambda: compare(b=future_mark), "FUTURE_ANCHOR_AT_GRADING")
        refuse("late publication cannot omit the clock binding", lambda: compare(published_at="2026-09-16T01:30:00.000001Z"), "PUBLICATION_AFTER_ENTRY_ANCHOR")
        refuse("grading just before source availability", lambda: compare(graded_at="2026-09-30T07:59:59.999999Z"), "FUTURE_SOURCE_AT_GRADING")
        # Reuse the exact retained early-review fixture, not the new producer's
        # reconstruction of it. Its whole source payload hash is preserved.
        early = json.loads((HERE/"prior_findings/vintage_repair_interface_review/EVIDENCE.json").read_bytes())
        vr1 = early["findings"][0]
        early_key = put_raw(encode(vr1["source_fixture"]))
        check("early_interface_source_payload_identity", early_key == vr1["source_sha256"], early_key)
        early_calendar = C.CalendarFixture(early["calendar_fixture"])
        refuse("V-R1 unselected future finalized row in whole blob", lambda: mark(early_key, session="2026-09-16", anchor="session_close", calendar=early_calendar),
               "SOURCE_PRECEDES_FINALIZED_BAR", finding="V-R1")
        reversed_blob = copy.deepcopy(vr1["source_fixture"]); reversed_blob["rows"].reverse()
        reverse_key = put_raw(encode(reversed_blob))
        refuse("whole-blob availability is invariant to row order", lambda: mark(reverse_key, session="2026-09-16", anchor="session_close", calendar=early_calendar), "SOURCE_PRECEDES_FINALIZED_BAR")
        endpoint_blob = put("000001.SZ", {"2026-09-16": stock_rows["2026-09-16"]}, available_at="2026-09-16T07:00:00Z")
        check("source_available_at_final_close_is_admissible", mark(endpoint_blob)["source"]["available_at"] == "2026-09-16T07:00:00+00:00")
        before_close = put("000001.SZ", {"2026-09-16": stock_rows["2026-09-16"]}, available_at="2026-09-16T06:59:59.999999Z")
        refuse("whole-blob availability one microsecond before finalized close", lambda: mark(before_close), "SOURCE_PRECEDES_FINALIZED_BAR")

        # V2: stored history is challenged before both idempotence and lookup.
        body = {"kind": "original_entry", "decision_id": "INDEPENDENT_SYNTHETIC_DECISION", "ticker": "000001.SZ",
                "entry_session": "2026-09-16", "price": 100, "basis": "t1_open", "recorded_at": "2026-09-16T08:00:00Z"}
        original = sealed(body)
        correction_body = {**body, "kind": "entry_correction", "price": 80, "basis": "t1_hl2",
                           "recorded_at": "2026-10-09T08:00:00Z", "correction_of": original["event_id"],
                           "reason": "Separate declared price/basis comparison; original retained"}
        correction = sealed(correction_body)
        ledger = [original]; saved_ledger = copy.deepcopy(ledger)
        corrected = C.append_event(ledger, correction)
        check("independently_sealed_original_and_price_basis_correction", corrected == [original, correction] and ledger == saved_ledger)
        damaged = copy.deepcopy(ledger); damaged[0]["price"] = 80
        refuse("V2.1 damaged stored original before exact replay", lambda: C.append_event(damaged, original), "EVENT_HASH_MISMATCH", finding="V2.1")
        refuse("V2.2 damaged stored original before correction target lookup", lambda: C.append_event(damaged, correction), "EVENT_HASH_MISMATCH", finding="V2.2")
        shifted = sealed({**body, "entry_session": "2026-09-17", "recorded_at": "2026-09-17T08:00:00Z"})
        refuse("V2.3 changed entry session does not create another original", lambda: C.append_event(ledger, shifted), "ORIGINAL_ENTRY_IMMUTABLE", finding="V2.3")
        vr2 = early["findings"][1]
        refuse("V-R2 exact retained equal-time correction", lambda: C.append_event(vr2["input_ledger"], vr2["proposed_correction"]),
               "CORRECTION_NOT_AFTER_ORIGINAL", finding="V-R2")
        for label, changes, reason in [
            ("equal time expressed in China timezone", {"recorded_at": "2026-09-16T16:00:00+08:00"}, "CORRECTION_NOT_AFTER_ORIGINAL"),
            ("earlier than original", {"recorded_at": "2026-09-16T07:59:59Z"}, "CORRECTION_NOT_AFTER_ORIGINAL"),
            ("changed entry session", {"entry_session": "2026-09-17"}, "CORRECTION_IDENTITY_MISMATCH"),
            ("blank reason", {"reason": " "}, "CORRECTION_REASON_UNAVAILABLE"),
            ("correction target is another correction", {"correction_of": correction["event_id"]}, "CORRECTION_TARGET_UNAVAILABLE")]:
            proposed = sealed({**correction_body, **changes})
            refuse("correction boundary " + label, lambda proposed=proposed: C.append_event(corrected, proposed), reason)
        later = sealed({**correction_body, "recorded_at": "2026-09-16T08:00:00.000001Z"})
        check("strictly_later_one_microsecond_correction_accepted", C.append_event(ledger, later) == [original, later])
        # A correction need only follow its original under this bounded schema;
        # there is no implied global time order or corrected-view folding rule.
        independent_append = C.append_event(corrected, later)
        check("clock_rule_is_later_than_original_not_global_correction_order", independent_append == [original, correction, later],
              {"premise": "No current-view precedence or total event-time ordering is certified."}, family="scope")
        unrelated = sealed({**body, "decision_id": "OTHER_SYNTHETIC_DECISION", "ticker": "000002.SZ"})
        damaged_unrelated = copy.deepcopy(unrelated); damaged_unrelated["price"] = 1
        bad_kind = sealed({**body, "decision_id": "OTHER_SYNTHETIC_DECISION", "kind": "unknown_event"})
        for label, prior_rows, reason in [
            ("later unrelated damaged row", [original, damaged_unrelated], "EVENT_HASH_MISMATCH"),
            ("later nonobject", [original, "damaged stored tail"], "EVENT_INVALID"),
            ("later unknown event kind", [original, bad_kind], "EVENT_KIND_UNSUPPORTED"),
            ("later second original with shifted session", [original, shifted], "ORIGINAL_ENTRY_IMMUTABLE"),
            ("later duplicated authentic event", [original, unrelated, unrelated], "LEDGER_DUPLICATE_EVENT_ID")]:
            refuse("all-existing-ledger validation before idempotence: " + label,
                   lambda prior_rows=prior_rows: C.append_event(prior_rows, original), reason)
        stored_bad_correction = copy.deepcopy(correction); stored_bad_correction["reason"] = "replaced without updating hash"
        refuse("all-existing correction validation before unrelated append", lambda: C.append_event([original, stored_bad_correction], unrelated), "EVENT_HASH_MISMATCH")
        check("caller_inputs_unmodified_after_refused_and_admitted_appends", ledger == saved_ledger and original == sealed(body))
        # Content integrity is intentionally not external custody authenticity.
        self_consistent_replacement = sealed({**body, "price": 1})
        check("self_consistent_unanchored_ledger_requires_external_custody", C.append_event([self_consistent_replacement], self_consistent_replacement) == [self_consistent_replacement],
              {"premise": "Rehashing an entirely replaced history cannot be detected without the incumbent store's trusted original identity/custody."}, family="scope")

        # V3: opening-quality result and row/field identity must meet at admission.
        corrupt_bar = {"open": 9, "high": 4.9, "low": 4.7, "close": 4.85, "volume": 100}
        bad_bench = put("510300.SS", {"2026-09-16": corrupt_bar, "2026-09-29": {"close": 5.2}})
        refuse("V3.1 retained out-of-range observation cannot become opening mark", lambda: mark(bad_bench, "510300.SS"), "OPEN_OUTSIDE_RANGE", finding="V3.1")
        price_mutation = copy.deepcopy(se); price_mutation["price"] = 80
        refuse("V3.2 altered mark price with unchanged row/source identity", lambda: compare(a=price_mutation), "MARK_SOURCE_BINDING_MISMATCH", finding="V3.2")
        for field, value in [("bar_row_sha256", "a"*64), ("calendar_id", "b"*64), ("basis_id", "UNBOUND_BASIS"), ("price", True)]:
            altered = copy.deepcopy(se); altered[field] = value
            refuse("serialized mark binding: " + field, lambda altered=altered: compare(a=altered), "MARK_SOURCE_BINDING_MISMATCH")
        changed_field = copy.deepcopy(se); changed_field["anchor"] = "session_close"; changed_field["anchor_at"] = calendar.resolve("2026-09-16", "session_close").isoformat()
        refuse("changing anchor label does not reuse an open as close", lambda: compare(a=changed_field), "MARK_SOURCE_BINDING_MISMATCH")
        changed_row = copy.deepcopy(se); changed_row["session"] = "2026-09-17"; changed_row["anchor_at"] = calendar.resolve("2026-09-17", "session_open").isoformat()
        refuse("changing session does not reuse another row's price", lambda: compare(a=changed_row), "MARK_SOURCE_BINDING_MISMATCH")
        refuse("supplied bar cannot replace exact source row", lambda: mark(supplied_bar={**stock_rows["2026-09-16"], "open": 80}), "SUPPLIED_BAR_SOURCE_MISMATCH")
        refuse("source bytes substituted beneath valid hash", lambda: compare(resolve_source=lambda _: b"{}"), "SOURCE_BYTES_HASH_MISMATCH")
        missing = copy.deepcopy(se); missing["source"]["sha256"] = "e"*64
        refuse("valid-looking source digest without bytes", lambda: compare(a=missing), "SOURCE_BYTES_UNAVAILABLE")
        wrong_adjustment = copy.deepcopy(se); wrong_adjustment["source"]["price_adjustment"] = "vendor_adjusted_price"
        refuse("adjustment metadata cannot float free of source", lambda: compare(a=wrong_adjustment), "MARK_SOURCE_BINDING_MISMATCH")
        duplicate = json.loads(blobs[sk]); duplicate["rows"].insert(1, copy.deepcopy(duplicate["rows"][0])); dupe_key = put_raw(encode(duplicate))
        refuse("duplicate source row cannot win by order", lambda: mark(dupe_key), "SOURCE_DUPLICATE_SESSION")
        duplicate_key_bytes = blobs[sk].replace(b'"open":100', b'"open":100,"open":80', 1)
        assert duplicate_key_bytes != blobs[sk]
        dupe_field = put_raw(duplicate_key_bytes)
        refuse("duplicate JSON field cannot win by order", lambda: mark(dupe_field), "SOURCE_DUPLICATE_JSON_KEY")
        changed_calendar_sessions = copy.deepcopy(sessions)
        changed_calendar_sessions["2026-09-16"]["session_open"] = "2026-09-16T09:31:00+08:00"
        changed_calendar = C.CalendarFixture(changed_calendar_sessions)
        refuse("different calendar receipt invalidates old serialized mark", lambda: compare(calendar=changed_calendar), "MARK_SOURCE_BINDING_MISMATCH")
        invalid_calendar = copy.deepcopy(sessions); invalid_calendar["2026-09-16"]["session_open"] = "2026-10-02T01:30:00Z"
        refuse("calendar cannot bind an anchor to an unrelated date", lambda: C.CalendarFixture(invalid_calendar), "CALENDAR_SESSION_CLOCK_MISMATCH")
        refuse("custody event cannot bypass market-source admission", lambda: C.validate_mark(original, "2026-10-09T08:00:00Z", resolve_source=blobs.__getitem__, calendar=calendar), "EXECUTION_RECEIPT_NOT_IMPLEMENTED")

        # Exact native required-field projection is an independent oracle for
        # the optional retention seam, without importing any collector.
        native_path = ROOT / "reviews/vintage_review/pinned_china_prices.py"
        text = native_path.read_text()
        method = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name == "_extract")
        ns = {"pd": pd, "log": logging.getLogger("independent_vintage_native")}
        exec(compile(ast.Module(body=[method], type_ignores=[]), "immutable_native_extract", "exec"), ns)
        native_extract = ns["_extract"]
        dates = pd.to_datetime(["2026-09-16", "2026-09-17"])
        frame = pd.DataFrame({"Open": [4.8, 4.85], "High": [4.9, 4.95], "Low": [4.7, 4.8], "Close": [4.85, 4.9], "Volume": [100.0, 101.0]}, index=dates)
        retention_cases = [
            ("numeric string open", "Open", "4.8", "OPEN_INVALID", "V4.1"),
            ("vendor token open", "Open", "vendor-missing", "OPEN_INVALID", "V4.2"),
            ("vendor token high", "High", "vendor-missing", "RANGE_INVALID", "V4.3"),
            ("Boolean open", "Open", True, "OPEN_INVALID", None),
            ("huge integer open", "Open", 10**400, "OPEN_INVALID", None),
            ("missing open", "Open", None, "OPEN_UNAVAILABLE", None),
            ("NaN open", "Open", float("nan"), "OPEN_UNAVAILABLE", None),
            ("reversed range", "High", 4.6, "RANGE_INVALID", None),
            ("invalid dictionary range", "Low", {"value": 4.7}, "RANGE_INVALID", None),
            ("outside range", "Open", 9, "OPEN_OUTSIDE_RANGE", None)]
        for label, column, value, expected, finding in retention_cases:
            f = frame.copy(); f[column] = f[column].astype(object); f.at[dates[0], column] = value
            out, diag = R.retain_optional_ohlcv(f, "510300.SS")
            projection_good = True
            try: pd.testing.assert_frame_equal(out[["close", "volume"]], native_extract(None, f, "510300.SS"))
            except AssertionError: projection_good = False
            raw = out.at[dates[0], column.lower()]
            raw_preserved = (isinstance(value, float) and math.isnan(value) and isinstance(raw, float) and math.isnan(raw)) or raw == value
            observed = {k: out.at[dates[0], k] for k in out.columns}
            actual_reason = C.opening_refusal(observed)
            try: C.anchor_price(observed, "session_open")
            except C.EvidenceError as exc: mark_reason = str(exc)
            else: mark_reason = "ADMITTED"
            check("retention-to-admission compatibility: " + label,
                  projection_good and bool(raw_preserved) and actual_reason == expected and mark_reason == expected and
                  diag["opening_mark_refusals"] == [{"session": "2026-09-16", "reason": expected}],
                  {"value_type": type(value).__name__, "optional_value_repr": repr(value), "required_projection_equal": projection_good,
                   "raw_value_preserved": bool(raw_preserved), "shared_refusal": actual_reason, "opening_admission": mark_reason,
                   "close_diagnostic": C.anchor_price(observed, "session_close")}, finding, "retention")
        close_only = frame[["Close", "Volume"]]
        close_retained, close_diag = R.retain_optional_ohlcv(close_only, "510300.SS")
        pd.testing.assert_frame_equal(close_retained, native_extract(None, close_only, "510300.SS"))
        check("close_only_legacy_observations_survive_without_open_fabrication", close_diag["qualified_open_rows"] == 0,
              {"columns": list(close_retained), "diagnostic": close_diag}, family="retention")
        missing_volume = frame.drop(columns=["Volume"])
        check("required_missing_volume_stays_native_unavailable", R.retain_optional_ohlcv(missing_volume, "510300.SS")[0] is None and
              native_extract(None, missing_volume, "510300.SS") is None, family="retention")

        # V5 and independent observable properties on frozen actual evidence.
        old = {"open": 100, "high": 102, "low": 98, "close": 101}
        for number, scale in [(1, 0), (2, -0.8)]:
            got = S.classify_bar(old, {k: v*scale for k,v in old.items()})
            check("V5 nonpositive shape factor " + str(scale), got == "invalid_ohlc", {"scale": scale, "classification": got}, "V5."+str(number), "empirical")
        check("positive_uniform_scale_control", S.classify_bar(old, {k:v*0.8 for k,v in old.items()}) == "uniform_ohlc_scale", family="empirical")
        entries = json.loads((ROOT / "vintage_lab/entry_comparison_rows.json").read_bytes())
        historical = json.loads((ROOT / "vintage_lab/historical_witness_rows.json").read_bytes())
        by_key = {(r["date"],r["ticker"]): r for r in entries}
        counts = Counter(); changed = []; positive_factors = []; scale_invalid = []
        for row in historical:
            if row["status"] != "bar_present": continue
            current = by_key[row["date"],row["ticker"]]["current_bar"]
            got = S.classify_bar(row["bar"], current); counts[got] += 1
            if got != row["change_shape"]: changed.append([row["date"],row["ticker"],row["label"],got,row["change_shape"]])
            if row["change_shape"] == "uniform_ohlc_scale":
                values = [row["bar"][k] for k in old] + [current[k] for k in old]
                positive = all(isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v) and v > 0 for v in values)
                factor = current["open"] / row["bar"]["open"] if positive else None
                consistent = positive and all(math.isclose(current[k], row["bar"][k]*factor, rel_tol=1.001e-5, abs_tol=0) for k in old)
                if not consistent: scale_invalid.append([row["date"],row["ticker"],row["label"]])
                else: positive_factors.append(factor)
        check("all_1332_present_witness_shapes_unchanged", sum(counts.values()) == 1332 and not changed,
              {"present_n": sum(counts.values()), "all_retained_rows": len(historical), "classifications": dict(counts), "changed": changed}, family="empirical")
        check("actual_uniform_scale_positive_property_independently_rechecked", bool(positive_factors) and not scale_invalid,
              {"uniform_scale_witness_n": len(positive_factors), "factor_min": min(positive_factors), "factor_max": max(positive_factors),
               "invalid": scale_invalid, "causal_attribution": "UNVERIFIED"}, family="empirical")
        check("all_1948_retained_entry_sessions_unchanged", len(entries) == 1948 and
              all(r["latched_t1_date"] == r["current_t1_date"] for r in entries),
              {"n": len(entries), "scope": "Equality of retained old/current dates; not a new calendar derivation or a replacement-session migration."}, family="empirical")
        # Explicit adapter boundaries, supported by executable positive controls.
        synthetic_sunday = C.CalendarFixture({"2026-09-20": {"session_open": "2026-09-20T09:30:00+08:00", "session_close": "2026-09-20T15:00:00+08:00"}})
        check("calendar_fixture_does_not_certify_exchange_session_truth", synthetic_sunday.resolve("2026-09-20", "session_open").isoformat() == "2026-09-20T01:30:00+00:00",
              {"premise": "The finite fixture validates date/anchor structure. Genuine exchange sessions must come from the incumbent calendar owner."}, family="scope")
        witnesses = {"kind": "EXPLICITLY_SYNTHETIC", "calendar": sessions,
                     "source_blobs_utf8": {k:v.decode() for k,v in blobs.items()}, "positive_marks": [se,sx,be,bx],
                     "positive_original": original, "positive_price_basis_correction": correction,
                     "source_codec_limit": "Test adapter only, with caller-declared availability/basis; no provider authenticity claim."}
    finally:
        for name, value in previous.items():
            if value is None: sys.modules.pop(name, None)
            else: sys.modules[name] = value

    for rel, identity in manifest["files"].items():
        check("frozen_candidate_unchanged_"+rel, sha((SNAPSHOT/rel).read_bytes()) == identity["sha256"], family="custody")
        assert sha((ROOT/"repairs/vintage_contract"/rel).read_bytes()) == identity["sha256"], rel
    for rel, identity in freeze["read_only_external_inputs"].items():
        assert sha((ROOT/rel).read_bytes()) == identity["sha256"], rel
    check("original_candidate_and_prior_empirical_review_inputs_unchanged", True,
          {"candidate_files": len(manifest["files"]), "prior_input_files": len(freeze["read_only_external_inputs"])}, family="custody")
    expected_original = {"V1.1","V1.2","V1.3","V2.1","V2.2","V2.3","V3.1","V3.2","V4.1","V4.2","V4.3","V5.1","V5.2"}
    check("all_13_original_variants_and_2_early_findings_exercised", set(findings) == expected_original|{"V-R1","V-R2"} and all(v=="CLOSED" for v in findings.values()), findings, family="coverage")
    failed = [x for x in checks if not x["passed"]]
    output = {"schema": "independent_vintage_repair_acceptance_v1",
              "status": "ACCEPTED_BOUNDED_RESEARCH_CONTRACT" if not failed else "REVIEW_COMPLETE_WITH_BLOCKERS",
              "source_sha": "3d90aad6d83152dfeeaf8345bc995826ac9d3139", "candidate_manifest_sha256": EXPECTED_MANIFEST,
              "candidate_contract_sha256": EXPECTED_CONTRACT, "review_script_sha256": sha(Path(__file__).read_bytes()),
              "producer_reproduction": {"tests": pr["test_count"], "result_sha256": sha((replay/"results.json").read_bytes()),
                                        "fixture_sha256": sha((replay/"fixtures.json").read_bytes())},
              "check_count": len(checks), "passed_n": len(checks)-len(failed), "failed_n": len(failed),
              "families": dict(Counter(x["family"] for x in checks)), "finding_closure": findings,
              "checks": checks, "remaining_blockers": failed,
              "scope_qualifications": [
                  "Authenticates declared record content against hashes, not the external producer or a wholly rewritten self-consistent history.",
                  "The synthetic calendar proves structure/binding, not actual exchange session truth; the JSON codec is not a production store.",
                  "Whole-blob availability is checked against every finalized row. Declared fixture times do not establish historical first-seen availability.",
                  "Strict correction chronology means later than the original, not a total ordering of independent corrections or a corrected-view fold.",
                  "Entry session is protected original identity; changing it is refused on originals and corrections. General replacement-session migration is not implemented.",
                  "Actual Parquet/source/basis/calendar adapters, canonical append custody and natural production lifecycle acceptance remain with existing owners.",
                  "Every comparison remains ALIGNED_MARK_DIAGNOSTIC / MARK_ONLY: no actual fill, total-return, cost or original-decision-knowability certification."],
              "runtime": {"python": sys.version, "pandas": pd.__version__},
              "effects": {"production_edits":0,"collector_calls":0,"vendor_calls":0,"cache_writes":0,"latch_writes":0,"publication_calls":0}}
    (HERE/"independent_fixtures.json").write_text(json.dumps(witnesses, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+"\n")
    (HERE/"ACCEPTANCE_RESULTS.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps({"status":output["status"],"checks":len(checks),"passed":len(checks)-len(failed),"failed":len(failed),
                      "producer_tests":pr["test_count"],"closed_findings":len([v for v in findings.values() if v=="CLOSED"])}))
    if failed: raise SystemExit(1)


if __name__ == "__main__": main()
