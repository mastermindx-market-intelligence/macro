#!/usr/bin/env python3
"""Coupled falsifiers: synthetic contract inputs plus hash-bound native rows."""
from __future__ import annotations
import ast
import collections
import copy
import hashlib
import json
import logging
import math
from pathlib import Path

import pandas as pd

from contract import (CalendarFixture, EvidenceError, aligned_excess, anchor_price,
                      append_event, canonical_bytes, digest, legacy_snapshot,
                      mark_from_source, opening_refusal, seal_event)
from retention import retain_optional_ohlcv
from shape import classify_bar

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"
INPUT_IDENTITIES = {
    "vintage_lab/entry_comparison_rows.json": "25160d291bec91cb7ba6fe77ac1e69ed5043f89f507dd369d4b32d0314c2e30c",
    "vintage_lab/historical_witness_rows.json": "aaf1d164616d2cd459774360cc8893d9ae181a56caeaa77b2f2aa05a827805fd",
    "reviews/vintage_review/pinned_china_prices.py": "fddb468e6cb2c6a1bf86235c337d6ad3b52cb34b0702510f3352c91b3e9a3b5a",
    "reviews/vintage_review/VINTAGE_INDEPENDENT_REVIEW.md": "e7ad8ac0a3aeec15183c542ce8d7f7ba691b19404730e552e28df99f7bc8160b",
}


def fixtures():
    days = ("2026-09-16", "2026-09-17", "2026-09-29", "2026-09-30", "2026-10-12")
    sessions = {day: {"session_open": day + "T09:30:00+08:00",
                      "session_close": day + "T15:00:00+08:00"} for day in days}
    calendar = CalendarFixture(sessions)
    blobs = {}

    def add(ticker, rows, *, basis=None, available_at="2026-10-09T08:00:00Z", **overrides):
        source = {"schema": "research.price_fixture.v2", "fixture_only": True,
                  "ticker": ticker, "provider_id": "synthetic-provider-for-contract-test",
                  "basis_id": basis or "synthetic-" + ticker + "-v1",
                  "price_adjustment": "unadjusted", "clock_kind": "producer_available_at",
                  "available_at": available_at,
                  "rows": [{"session": day, "bar": bar} for day, bar in rows.items()]}
        source.update(overrides)
        raw = canonical_bytes(source)
        sha = hashlib.sha256(raw).hexdigest()
        blobs[sha] = raw
        return sha

    stock_rows = {"2026-09-16": {"open": 100, "high": 102, "low": 99, "close": 101},
                  "2026-09-29": {"close": 110}, "2026-09-30": {"close": 112}}
    bench_rows = {"2026-09-16": {"open": 200, "high": 202, "low": 199, "close": 201},
                  "2026-09-29": {"close": 220}, "2026-09-30": {"close": 222}}
    stock = add("000001.SZ", stock_rows)
    bench = add("510300.SS", bench_rows)
    return sessions, calendar, blobs, add, stock_rows, bench_rows, stock, bench


def main():
    initial = {}
    for path, expected in INPUT_IDENTITIES.items():
        raw = (ROOT / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, path
        initial[path] = {"sha256": expected, "bytes": len(raw)}
    tests = []

    def passed(name, details=None, family="contract"):
        tests.append({"name": name, "status": "PASS", "family": family, "details": details})

    def reject(name, expected, operation, family="contract"):
        try:
            operation()
        except EvidenceError as exc:
            allowed = {expected} if isinstance(expected, str) else set(expected)
            assert str(exc) in allowed, (name, str(exc), allowed)
            passed(name, {"refused_with": str(exc)}, family)
        else:
            raise AssertionError("incorrect admission: " + name)

    sessions, calendar, blobs, add, sr, br, stock, bench = fixtures()

    def make(sha, ticker, session, anchor="session_open", **kwargs):
        return mark_from_source(ticker=ticker, session=session, anchor=anchor,
                                source_sha256=sha, resolve_source=blobs.__getitem__,
                                calendar=calendar, **kwargs)

    se = make(stock, "000001.SZ", "2026-09-16")
    sx = make(stock, "000001.SZ", "2026-09-29", "session_close")
    be = make(bench, "510300.SS", "2026-09-16")
    bx = make(bench, "510300.SS", "2026-09-29", "session_close")
    kwargs = {"published_at": "2026-09-15T08:00:00Z", "graded_at": "2026-10-09T08:01:00Z",
              "entry_anchor_at": "2026-09-16T01:30:00Z", "resolve_source": blobs.__getitem__, "calendar": calendar}

    def compare(a=se, b=sx, c=be, d=bx, **change):
        return aligned_excess(a, b, c, d, **{**kwargs, **change})

    result = compare()
    assert result["execution_status"] == "MARK_ONLY" and math.isclose(result["excess_pp"], 0, abs_tol=1e-12)
    passed("same-vintage same-anchor arithmetic is admitted with derived endpoint clocks", result)
    assert compare(entry_anchor_at=None) == result
    passed("free entry timestamp is unnecessary; exact calendar-derived clock suffices")
    assert compare(published_at="2026-09-16T09:30:00+08:00") == result
    passed("equivalent aware timezone and publication at the declared mark boundary")
    reject("missing publication clock", "PUBLICATION_CLOCK_UNVERIFIED", lambda: compare(published_at=None))
    reject("late publication even without supplied anchor", "PUBLICATION_AFTER_ENTRY_ANCHOR", lambda: compare(published_at="2026-10-01T08:00:00Z", entry_anchor_at=None))
    reject("V1 unrelated October entry timestamp cannot excuse September entry", "ENTRY_CLOCK_BINDING_MISMATCH", lambda: compare(published_at="2026-10-01T08:00:00Z", entry_anchor_at="2026-10-02T01:30:00Z"))
    reject("V1 impossible September 31 is refused before lexical comparison", "SESSION_INVALID", lambda: make(stock, "000001.SZ", "2026-09-31"))
    reject("valid date absent from supplied calendar remains unqualified", "SESSION_NOT_IN_CALENDAR", lambda: make(stock, "000001.SZ", "2026-09-18"))
    bad_calendar = copy.deepcopy(sessions)
    bad_calendar["2026-09-16"]["session_open"] = "2026-10-02T01:30:00Z"
    reject("calendar receipt cannot map an unrelated date to the entry", "CALENDAR_SESSION_CLOCK_MISMATCH", lambda: CalendarFixture(bad_calendar))
    bad_calendar = copy.deepcopy(sessions)
    bad_calendar["2026-09-16"]["session_open"] = "2026-09-16T16:00:00+08:00"
    reject("calendar open after close", "CALENDAR_ANCHOR_ORDER_INVALID", lambda: CalendarFixture(bad_calendar))
    bad_calendar = copy.deepcopy(sessions)
    bad_calendar["2026-09-16"]["session_close"] = "2026-09-16T15:00:00"
    reject("naive calendar clock", "CLOCK_TIMEZONE_MISSING", lambda: CalendarFixture(bad_calendar))
    future_rows = {"2026-10-12": {"close": 120}}
    early_future = add("000001.SZ", future_rows)
    reject("V1 future finalized bar cannot have an earlier source availability", "SOURCE_PRECEDES_FINALIZED_BAR", lambda: make(early_future, "000001.SZ", "2026-10-12", "session_close"))
    mixed_future = add("000001.SZ", {"2026-09-16": sr["2026-09-16"], **future_rows}, available_at="2026-09-16T08:00:00Z")
    reject("blob-wide early availability cannot hide an unselected future finalized row", "SOURCE_PRECEDES_FINALIZED_BAR", lambda: make(mixed_future, "000001.SZ", "2026-09-16", "session_close"))
    real_future = add("000001.SZ", {**sr, **future_rows}, available_at="2026-10-12T08:00:00Z")
    future_mark = make(real_future, "000001.SZ", "2026-10-12", "session_close")
    reject("future exit cannot be graded before its own anchor", "FUTURE_ANCHOR_AT_GRADING", lambda: compare(b=future_mark))
    late_source = add("000001.SZ", sr, available_at="2026-10-10T08:00:00Z")
    late_mark = make(late_source, "000001.SZ", "2026-09-16")
    reject("otherwise historical mark uses source unavailable at grading", "FUTURE_SOURCE_AT_GRADING", lambda: compare(a=late_mark))
    git_source = add("000001.SZ", sr, clock_kind="git_committer_time")
    reject("Git clock cannot substitute for producer availability", "SOURCE_AVAILABILITY_UNVERIFIED", lambda: make(git_source, "000001.SZ", "2026-09-16"))
    reject("close cannot replace benchmark opening comparator", "ENTRY_ANCHOR_MISMATCH", lambda: compare(c=make(bench, "510300.SS", "2026-09-16", "session_close")))
    reject("exit comparator must use exact same session", "EXIT_ANCHOR_MISMATCH", lambda: compare(d=make(bench, "510300.SS", "2026-09-30", "session_close")))
    reject("HL2 never acquires a clock", "HL2_EXACT_TIME_UNAVAILABLE", lambda: make(stock, "000001.SZ", "2026-09-16", "hl2_proxy"))
    alt_basis = add("000001.SZ", sr, basis="synthetic-stock-v2")
    reject("resolved different basis is refused", "BASIS_ID_MISMATCH", lambda: compare(b=make(alt_basis, "000001.SZ", "2026-09-29", "session_close")))
    alt_vintage = add("000001.SZ", sr, available_at="2026-10-09T08:00:01Z")
    reject("same basis does not excuse two source vintages", "WITHIN_INSTRUMENT_VINTAGE_MISMATCH", lambda: compare(b=make(alt_vintage, "000001.SZ", "2026-09-29", "session_close")))

    for field, value in [("price", 80), ("bar_row_sha256", "b" * 64), ("basis_id", "forged"), ("anchor_at", "2026-09-17T01:30:00Z"), ("calendar_id", "c" * 64), ("price", True)]:
        bad = copy.deepcopy(se)
        bad[field] = value
        reject("V3 deserialized mark cannot alter " + field + ":" + str(value), "MARK_SOURCE_BINDING_MISMATCH", lambda bad=bad: compare(a=bad))
    for field, value in [("available_at", "2026-09-29T08:00:00+00:00"), ("price_adjustment", "vendor_adjusted_price"), ("provider_id", "another-provider")]:
        bad = copy.deepcopy(se)
        bad["source"][field] = value
        reject("source metadata copied onto a mark stays bound: " + field, "MARK_SOURCE_BINDING_MISMATCH", lambda bad=bad: compare(a=bad))
    bad = copy.deepcopy(se)
    bad["source"]["sha256"] = "a" * 64
    reject("a well-shaped free hash cannot stand in for bytes", "SOURCE_BYTES_UNAVAILABLE", lambda: compare(a=bad))
    reject("source bytes cannot be substituted under an unchanged hash", "SOURCE_BYTES_HASH_MISMATCH", lambda: compare(resolve_source=lambda key: b"{}"))
    reject("constructor supplied bar must be the exact resolved source row", "SUPPLIED_BAR_SOURCE_MISMATCH", lambda: make(stock, "000001.SZ", "2026-09-16", supplied_bar={**sr["2026-09-16"], "open": 80}))
    assert make(stock, "000001.SZ", "2026-09-16", supplied_bar=sr["2026-09-16"]) == se
    passed("exact caller bar and source row agree")
    duplicate = json.loads(blobs[stock])
    duplicate["rows"].append(copy.deepcopy(duplicate["rows"][0]))
    raw = canonical_bytes(duplicate)
    key = hashlib.sha256(raw).hexdigest()
    blobs[key] = raw
    reject("duplicate source sessions refused even when byte hash is correct", "SOURCE_DUPLICATE_SESSION", lambda: make(key, "000001.SZ", "2026-09-16"))
    malformed = b'{"schema":"research.price_fixture.v2","schema":"research.price_fixture.v2"}'
    key = hashlib.sha256(malformed).hexdigest()
    blobs[key] = malformed
    reject("duplicate JSON identity keys refused", "SOURCE_DUPLICATE_JSON_KEY", lambda: make(key, "000001.SZ", "2026-09-16"))
    for price_adjustment in (None, "", "raw-because-the-caller-says-so", ["unadjusted"]):
        key = add("000001.SZ", sr, price_adjustment=price_adjustment)
        reject("source adjustment contract unavailable " + str(price_adjustment), "PRICE_ADJUSTMENT_UNAVAILABLE", lambda key=key: make(key, "000001.SZ", "2026-09-16"))
    reject("canonical instrument mismatch", "SOURCE_INSTRUMENT_MISMATCH", lambda: make(stock, "000002.SZ", "2026-09-16"))
    reject("missing exact source row", "SOURCE_ROW_UNAVAILABLE", lambda: make(stock, "000001.SZ", "2026-09-17"))

    # Optional-field compatibility with exact pinned native code, no collector import.
    source = (ROOT / "reviews/vintage_review/pinned_china_prices.py").read_text()
    method = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == "_extract")
    ns = {"pd": pd, "log": logging.getLogger("vintage_contract_repair")}
    exec(compile(ast.Module(body=[method], type_ignores=[]), "pinned_native_extract", "exec"), ns)
    native = ns["_extract"]
    index = pd.DatetimeIndex(["2026-09-16", "2026-09-17"])
    frame = pd.DataFrame({"Open": [4.8, 4.85], "High": [4.9, 4.95], "Low": [4.7, 4.8], "Close": [4.85, 4.9], "Volume": [100.0, 101.0]}, index=index)
    incumbent = native(None, frame, "510300.SS")
    retained, diagnostics = retain_optional_ohlcv(frame, "510300.SS")
    assert list(incumbent) == ["close", "volume"] and diagnostics["qualified_open_rows"] == 2
    pd.testing.assert_frame_equal(retained[["close", "volume"]], incumbent)
    passed("native extractor loses OHLC; repaired optional retention preserves incumbent required projection", diagnostics, "retention")
    multi = pd.concat({"510300.SS": frame}, axis=1)
    pd.testing.assert_frame_equal(retain_optional_ohlcv(multi, "510300.SS")[0], retained)
    passed("single and MultiIndex provider shapes agree", family="retention")
    values = [("numeric string open", "Open", "4.8", "OPEN_INVALID"),
              ("vendor token open", "Open", "vendor-missing", "OPEN_INVALID"),
              ("vendor token high", "High", "vendor-missing", "RANGE_INVALID"),
              ("zero open", "Open", 0, "OPEN_INVALID"),
              ("negative open", "Open", -1, "OPEN_INVALID"),
              ("Boolean open", "Open", True, "OPEN_INVALID"),
              ("huge integer open", "Open", 10 ** 400, "OPEN_INVALID"),
              ("NaN open", "Open", float("nan"), "OPEN_UNAVAILABLE"),
              ("infinite open", "Open", float("inf"), "OPEN_INVALID"),
              ("list open", "Open", [4.8], "OPEN_INVALID"),
              ("dictionary high", "High", {"value": 4.9}, "RANGE_INVALID"),
              ("corrupt open outside range", "Open", 9, "OPEN_OUTSIDE_RANGE")]
    for label, column, value, reason in values:
        mutated = frame.copy()
        mutated[column] = mutated[column].astype(object)
        mutated.at[index[0], column] = value
        candidate, diag = retain_optional_ohlcv(mutated, "510300.SS")
        pd.testing.assert_frame_equal(candidate[["close", "volume"]], native(None, mutated, "510300.SS"))
        assert diag["opening_mark_refusals"] == [{"session": "2026-09-16", "reason": reason}], (label, diag)
        observed = {column: candidate.at[index[0], column] for column in candidate.columns}
        assert opening_refusal(observed) == reason
        reject("V3/V4 retention and mark-price admission agree: " + label, reason, lambda observed=observed: anchor_price(observed, "session_open"), "retention")
        assert anchor_price(observed, "session_close") == 4.85
        passed("malformed optional field preserves required observations and close diagnostic: " + label, family="retention")
    corrupted_bench = add("510300.SS", {**br, "2026-09-16": {"open": 9, "high": 4.9, "low": 4.7, "close": 4.85}})
    reject("V3 exact retained corrupt bar cannot become a resolved opening mark", "OPEN_OUTSIDE_RANGE", lambda: make(corrupted_bench, "510300.SS", "2026-09-16"))
    close_only = frame[["Close", "Volume"]]
    retained, diag = retain_optional_ohlcv(close_only, "510300.SS")
    pd.testing.assert_frame_equal(retained, incumbent)
    assert diag["qualified_open_rows"] == 0
    passed("legacy close-only schema stays close-only", diag, "retention")
    close_source = add("510300.SS", {"2026-09-16": {"close": 4.85, "volume": 100}, "2026-09-29": {"close": 5.335}})
    reject("benchmark opening mark cannot be fabricated from Close", "OPEN_UNAVAILABLE", lambda: make(close_source, "510300.SS", "2026-09-16"))
    close_result = compare(a=make(stock, "000001.SZ", "2026-09-16", "session_close"),
                           c=make(close_source, "510300.SS", "2026-09-16", "session_close"),
                           d=make(close_source, "510300.SS", "2026-09-29", "session_close"), entry_anchor_at=None)
    assert close_result["status"] == "ALIGNED_MARK_DIAGNOSTIC"
    passed("same-anchor close diagnostic remains available without opening data", close_result, "retention")
    for label, frame_bad in [("missing Close", frame.drop(columns=["Close"])), ("missing Volume", frame.drop(columns=["Volume"])), ("all closes missing", frame.assign(Close=float("nan"))), ("empty", frame.iloc[:0])]:
        assert native(None, frame_bad, "510300.SS") is None
        assert retain_optional_ohlcv(frame_bad, "510300.SS")[0] is None
        passed("incumbent empty/required-field refusal remains: " + label, family="retention")

    # Existing records must authenticate before either fast replay or correction.
    original_body = {"kind": "original_entry", "decision_id": "synthetic-decision-001", "ticker": "000001.SZ", "entry_session": "2026-09-16", "price": 100, "basis": "t1_open", "recorded_at": "2026-09-16T08:00:00Z"}
    original = seal_event(original_body)
    ledger = append_event([], original)
    assert append_event(ledger, original) == ledger and ledger == [original]
    passed("authentic original replay is idempotent and input remains unchanged", family="ledger")
    correction_body = {**original_body, "kind": "entry_correction", "price": 80,
                       "correction_of": original["event_id"], "reason": "Synthetic new comparison; original retained",
                       "recorded_at": "2026-10-09T08:00:00Z"}
    correction = seal_event(correction_body)
    amended = append_event(ledger, correction)
    assert amended == [original, correction] and ledger == [original] and append_event(amended, correction) == amended
    passed("authenticated correction appends separately and replays idempotently", family="ledger")
    damaged = copy.deepcopy(ledger)
    damaged[0]["price"] = 80
    reject("V2 damaged prior original refused before original replay", "EVENT_HASH_MISMATCH", lambda: append_event(damaged, original), "ledger")
    reject("V2 damaged prior original refused before correction lookup", "EVENT_HASH_MISMATCH", lambda: append_event(damaged, correction), "ledger")
    altered = seal_event({**original_body, "price": 80})
    reject("rehashed replacement cannot overwrite original", "ORIGINAL_ENTRY_IMMUTABLE", lambda: append_event(ledger, altered), "ledger")
    shifted = seal_event({**original_body, "entry_session": "2026-09-17", "recorded_at": "2026-09-17T08:00:00Z"})
    reject("V2 changing original entry session cannot evade stable decision/ticker key", "ORIGINAL_ENTRY_IMMUTABLE", lambda: append_event(ledger, shifted), "ledger")
    reject("stored second original refuses even on exact original replay", "ORIGINAL_ENTRY_IMMUTABLE", lambda: append_event([original, shifted], original), "ledger")
    reject("duplicate stored event IDs do not get collapsed", "LEDGER_DUPLICATE_EVENT_ID", lambda: append_event([original, original], correction), "ledger")
    damaged_correction = copy.deepcopy(amended)
    damaged_correction[1]["price"] = 90
    reject("existing correction body also authenticates on replay", "EVENT_HASH_MISMATCH", lambda: append_event(damaged_correction, original), "ledger")
    for name, changes, expected in [
        ("different correction ticker", {"ticker": "000002.SZ"}, "CORRECTION_IDENTITY_MISMATCH"),
        ("different correction session", {"entry_session": "2026-09-17"}, "CORRECTION_IDENTITY_MISMATCH"),
        ("missing reason", {"reason": ""}, "CORRECTION_REASON_UNAVAILABLE"),
        ("missing original target", {"correction_of": "b" * 64}, "CORRECTION_TARGET_UNAVAILABLE"),
        ("correction targets correction", {"correction_of": correction["event_id"]}, "CORRECTION_TARGET_UNAVAILABLE"),
        ("correction recorded earlier than original", {"recorded_at": "2026-09-16T07:59:00Z"}, "CORRECTION_NOT_AFTER_ORIGINAL"),
        ("correction recorded at equal time to original", {"recorded_at": original["recorded_at"]}, "CORRECTION_NOT_AFTER_ORIGINAL"),
        ("nonexistent original session", {"entry_session": "2026-09-31"}, "SESSION_INVALID"),
        ("nonnumeric correction price", {"price": "80"}, "PRICE_INVALID"),
        ("Boolean correction price", {"price": True}, "PRICE_INVALID"),
        ("huge correction price", {"price": 10 ** 400}, "PRICE_INVALID"),
    ]:
        new_event = seal_event({**correction_body, **changes})
        reject(name, expected, lambda new_event=new_event: append_event(amended, new_event), "ledger")
    reject("correction cannot precede original in stored append order", "CORRECTION_TARGET_UNAVAILABLE", lambda: append_event([correction, original], original), "ledger")
    old_latch = {"date": "2026-09-15", "ticker": "000001.SZ", "entry": 100,
                 "basis_used": "t1_hl2", "t1_date": "2026-09-16", "corrupt_bar": True,
                 "latched_asof": "2026-09-16T08:00:00Z"}
    before = copy.deepcopy(old_latch)
    saved = legacy_snapshot(old_latch)
    assert saved["original"] == before == old_latch and saved["qualification"] == "LEGACY_SOURCE_VINTAGE_UNVERIFIED"
    passed("original seven legacy fields retained with unresolved vintage qualification", saved, "ledger")

    # Repaired positive-scale guard cannot silently relabel retained evidence.
    entries = json.loads((ROOT / "vintage_lab/entry_comparison_rows.json").read_text())
    witnesses = json.loads((ROOT / "vintage_lab/historical_witness_rows.json").read_text())
    by_key = {(r["date"], r["ticker"]): r for r in entries}
    classification_count = collections.Counter()
    checked = 0
    for row in witnesses:
        if row["status"] != "bar_present":
            continue
        classification = classify_bar(row["bar"], by_key[row["date"], row["ticker"]]["current_bar"])
        assert classification == row["change_shape"], (row["date"], row["ticker"], row["label"], classification, row["change_shape"])
        classification_count[classification] += 1
        checked += 1
    passed("all retained present-bar witness classifications remain unchanged", {"checked": checked, "classifications": dict(classification_count)}, "empirical_parity")
    old = {"open": 100, "high": 102, "low": 98, "close": 101}
    for scale in (0, -0.8):
        assert classify_bar(old, {k: v * scale for k, v in old.items()}) == "invalid_ohlc"
        passed("V5 nonpositive scale is refused: " + str(scale), family="empirical_parity")
    assert classify_bar(old, {k: v * 0.8 for k, v in old.items()}) == "uniform_ohlc_scale"
    passed("positive common scale remains identifiable without causal attribution", family="empirical_parity")
    corrupt = {"open": 16.3, "high": 17.7, "low": 17.4, "close": 17.5}
    healed = {**corrupt, "open": 17.5}
    assert classify_bar(corrupt, healed) == "open_only_rewrite"
    assert (corrupt["high"] + corrupt["low"]) / 2 == (healed["high"] + healed["low"]) / 2
    passed("healed open explains basis choice without changing original HL2 or assigning cause", family="empirical_parity")

    for path, expected in INPUT_IDENTITIES.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    passed("original empirical/source/review files unchanged during repair replay", family="custody")
    fixture = {"kind": "EXPLICITLY_SYNTHETIC", "calendar_sessions": sessions,
               "source_blobs_utf8": {key: value.decode() for key, value in blobs.items()},
               "positive_marks": [se, sx, be, bx], "positive_original": original,
               "positive_correction": correction}
    (HERE / "fixtures.json").write_text(json.dumps(fixture, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    result = {"status": "PASS", "study_pin": PIN, "test_count": len(tests),
              "families": dict(collections.Counter(row["family"] for row in tests)),
              "tests": tests, "source_input_identities": initial,
              "code_identities": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in ("contract.py", "retention.py", "shape.py", "verify.py")},
              "limits": ["Synthetic byte codec and calendar validate contracts, not vendor history or holiday truth.",
                         "Native _extract is AST-extracted from previously verified immutable bytes; no collector is imported or run.",
                         "No original empirical file, legacy latch, production source, runtime or stored operational record changes.",
                         "All return results are price-mark diagnostics, without actual-fill, total-return or historical knowability certification."]}
    (HERE / "results.json").write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "tests": len(tests), "families": result["families"], "present_witnesses_checked": checked}))


if __name__ == "__main__":
    main()
