#!/usr/bin/env python3
"""Independent read-only review of the frozen vintage laboratory.

All output is confined to this review directory. All adversarial bars/events
are synthetic. The canonical benchmark extractor is AST-extracted from an
independently fetched, Git-blob-verified source file; no collector is imported.
"""
from __future__ import annotations

import ast
import collections
import contextlib
import copy
import datetime as dt
import hashlib
import io
import json
import logging
import math
from pathlib import Path
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1] / "vintage_lab"
CENSUS = HERE.parents[2]
sys.path.insert(0, str(LAB))
import numpy as np
import pandas as pd
import benchmark_retention_probe as benchmark
import fill_vintage_contract as contract
import verify_vintage_contract as producer_verify
from collect_vintage_evidence import classify_bar

PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"


def read(name):
    return json.loads((LAB / name).read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def near(a, b):
    return a is not None and b is not None and math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a) - float(b)) <= max(abs(float(a)), abs(float(b)), 1.0) * 1e-6


def parse_clock(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    return parsed.astimezone(dt.timezone.utc)


def key(row):
    return row["date"], row["ticker"]


def stored_basis_value(bar, basis):
    if bar is None:
        return None
    if basis == "t1_open":
        return bar.get("open")
    if basis == "t1_close":
        return bar.get("close")
    if basis == "t1_hl2":
        return (bar["high"] + bar["low"]) / 2
    raise AssertionError("unexpected stored basis")


def independent_shape(old, new):
    fields = ("open", "high", "low", "close")
    if any(old.get(k) is None or new.get(k) is None for k in fields):
        return "incomplete_ohlc"
    differences = [k for k in fields if not near(old[k], new[k])]
    if not differences:
        return "identical_ohlc"
    if differences == ["open"]:
        return "open_only_rewrite"
    if all(math.isfinite(old[k]) and math.isfinite(new[k]) and old[k] > 0 and new[k] > 0 for k in fields):
        ratios = [new[k] / old[k] for k in fields]
        if max(ratios) - min(ratios) <= 1e-5 * max(ratios):
            return "uniform_ohlc_scale"
    # No retained real witness has an affine-only class; avoid borrowing the
    # producer's polynomial classifier for this independent real-data census.
    return "mixed_field_revision"


def main():
    checks = []
    findings = []
    initial = json.loads((HERE / "reviewed_input_identities.json").read_text())
    for name, identity in initial["files"].items():
        raw = (LAB / name).read_bytes()
        assert len(raw) == identity["bytes"] and sha(raw) == identity["sha256"] and git_blob(raw) == identity["git_blob"], name
    manifest = read("VINTAGE_MANIFEST.json")
    for name, identity in manifest["files"].items():
        assert initial["files"][name] == identity, name
    for name, identity in read("output_manifest.json").items():
        assert {k: initial["files"][name][k] for k in identity} == identity
    checks.append({"name": "all 18 frozen input files and both producer manifests agree", "status": "PASS"})

    # Reproduce both producer suites while redirecting their outputs here.
    with patch.object(sys, "argv", [str(LAB / "verify_vintage_contract.py"), "--evidence", str(LAB), "--out", str(HERE / "producer_contract_replay.json")]), contextlib.redirect_stdout(io.StringIO()):
        producer_verify.main()
    assert json.loads((HERE / "producer_contract_replay.json").read_text()) == read("vintage_contract_checks.json")
    source = (HERE / "pinned_china_prices.py").read_bytes()
    assert git_blob(source) == "4324c7299af32abd22380488e86d97abdc552f72"
    assert sha(source) == read("benchmark_retention_checks.json")["source_sha256"]

    def immutable_source_read(command, *args, **kwargs):
        assert command == ["git", "-C", "READ_ONLY_VERIFIED_SOURCE", "show", PIN + ":collectors/china_prices.py"]
        return source

    with patch.object(sys, "argv", [str(LAB / "benchmark_retention_probe.py"), "--repo", "READ_ONLY_VERIFIED_SOURCE", "--out", str(HERE / "producer_benchmark_replay.json")]), patch.object(benchmark.subprocess, "check_output", immutable_source_read), contextlib.redirect_stdout(io.StringIO()):
        benchmark.main()
    assert json.loads((HERE / "producer_benchmark_replay.json").read_text()) == read("benchmark_retention_checks.json")
    checks.append({"name": "producer 18 contract and 9 retention checks independently replay unchanged", "status": "PASS", "counts": [18, 9], "source_acquisition": "Independent GitHub immutable-file read, exact source Git blob and SHA-256 verified; only the script's source-read operation substituted."})

    rows = read("entry_comparison_rows.json")
    by_key = {key(row): row for row in rows}
    assert len(rows) == len(by_key) == 1948
    changed = {key(row) for row in rows if not near(row["latched_entry"], row["current_entry"])}
    assert changed == {key(row) for row in rows if row["changed"]}
    assert len(changed) == 656
    assert all(row["latched_t1_date"] == row["current_t1_date"] for row in rows)
    independent_classes = {}
    for row in rows:
        row_key = key(row)
        if row_key not in changed:
            label = "unchanged_derived_entry"
        elif near(stored_basis_value(row["current_bar"], row["latched_basis"]), row["latched_entry"]) and row["latched_basis"] != row["current_basis"]:
            label = "basis_selection_only_at_current_bar"
        elif near(stored_basis_value(row["raw_bar"], row["latched_basis"]), row["latched_entry"]) and not near(stored_basis_value(row["current_bar"], row["latched_basis"]), row["latched_entry"]):
            label = "latch_matches_current_raw_same_basis"
        else:
            label = "same_session_price_or_basis_revision_unresolved"
        assert label == row["classification"], row_key
        independent_classes[row_key] = label

    prior_bytes = (CENSUS / "v4_review_rows.json").read_bytes()
    assert sha(prior_bytes) == "626aacda09bdef9ba6cd8bb01a3688e445228b48ce63d5496defb07ce0482830"
    prior = json.loads(prior_bytes)["production_h10"]
    production = [dict(zip(prior["columns"], values)) for values in prior["data"]]
    mature_rows = [row for row in production if row["excess"] is not None]
    mature = {key(row) for row in mature_rows}
    assert len(mature_rows) == len(mature) == 289
    assert mature == {key(row) for row in rows if row["v4_mature"]}
    assert len(mature & changed) == 136
    assert len({row["date"] for row in mature_rows}) == 21
    summary = read("vintage_results.json")
    assert summary["all_latched_episode_rows"] == 2632 and summary["changed_episode_rows"] == 933
    # 2632/933 are episode-row counts in the prior CSV identity, not totals
    # recoverable by multiplying 1948/656 distinct entries. The V4 table is
    # separately retained and is fully reconstructed below.
    grouped = collections.defaultdict(list)
    for row in mature_rows:
        match = by_key[key(row)]
        assert near(row["entry"], match["current_entry"]) and near(row["latched_entry"], match["latched_entry"])
        grouped[independent_classes[key(row)]].append(row)
    accounting = {}
    for label, group in grouped.items():
        n = len(group)
        delta = math.fsum(row["excess"] - row["latch_excess"] for row in group)
        stats = {"n": n, "latched_mean_excess_pp": math.fsum(row["latch_excess"] for row in group) / n, "current_mean_excess_pp": math.fsum(row["excess"] for row in group) / n, "mean_current_minus_latched_pp": delta / n, "contribution_to_289_row_mean_difference_pp": delta / 289, "win_sign_changes": sum((row["excess"] > 0) != (row["latch_excess"] > 0) for row in group), "original_win_to_current_loss": sum(row["latch_excess"] > 0 >= row["excess"] for row in group), "original_loss_to_current_win": sum(row["latch_excess"] <= 0 < row["excess"] for row in group)}
        expected = summary["v4_fixed_current_exit_accounting_by_class"][label]
        for field, value in stats.items():
            assert math.isclose(value, expected[field], rel_tol=1e-10, abs_tol=1e-10), (label, field)
        accounting[label] = stats
    counts = {"unique_latches": len(rows), "changed_unique_latches": len(changed), "mature_v4_episodes": len(mature_rows), "mature_v4_dates": 21, "changed_mature_v4": len(mature & changed), "unchanged_mature_v4": len(mature - changed), "overlap_changed_and_mature": len(mature & changed), "union_witness_cohort": len(mature | changed), "changed_classes": dict(collections.Counter(independent_classes[k] for k in changed)), "mature_classes": dict(collections.Counter(independent_classes[k] for k in mature)), "mature_latched_basis": dict(collections.Counter(by_key[k]["latched_basis"] for k in mature)), "mature_hl2_corrupt_flags": sum(by_key[k]["latched_basis"] == "t1_hl2" and by_key[k]["latched_corrupt"] for k in mature)}
    checks.append({"name": "656 and 289 denominators, basis classes and all V4 accounting contributions independently reconstructed", "status": "PASS", "counts": counts})

    inputs = read("vintage_inputs.json")
    commits = {row["commit"]: parse_clock(row["committed_at"]) for row in inputs["reachable_price_commits"]}
    assert len(commits) == 82
    assert len(inputs["source_blobs"]) == summary["source_blob_count"] == 3360
    witnesses = read("historical_witness_rows.json")
    by_witness = {(key(row), row["label"]): row for row in witnesses}
    assert len(witnesses) == len(by_witness) == 2 * len(changed | mature) == 1618
    detailed_keys = changed | mature
    for row in witnesses:
        k = key(row)
        assert k in detailed_keys
        latch_clock = parse_clock(by_key[k]["latched_asof"])
        before = row["label"] == "nearest_commit_before_latch"
        candidates = [c for c, when in commits.items() if (when <= latch_clock if before else when >= latch_clock)]
        if not candidates:
            assert row["status"] == "no_reachable_commit_on_side"
            continue
        expected_clock = (max if before else min)(commits[c] for c in candidates)
        assert commits[row["commit"]] == expected_clock
        assert row["ancestor_of_study_pin"] is True
        assert row["witness_clock_source"] == "git_committer_time" and row["latch_clock_source"] == "entry_latch.parquet.latched_asof"
        assert parse_clock(row["committed_at"]) == expected_clock
        source_identity = inputs["source_blobs"][row["commit"] + ":" + row["path"]]
        assert len(source_identity["sha256"]) == 64 and len(source_identity["git_blob"]) == 40
        assert row["status"] == "bar_present"
        equals = near(stored_basis_value(row["bar"], by_key[k]["latched_basis"]), by_key[k]["latched_entry"])
        assert equals == row["matches_latch_same_basis"]
        assert independent_shape(row["bar"], by_key[k]["current_bar"]) == row["change_shape"]
    qualifications = {}
    for label, cohort in [("changed_656", changed), ("mature_v4_289", mature)]:
        counts_here = collections.Counter()
        shape_counts = collections.Counter()
        prior_shape_counts = collections.Counter()
        for k in cohort:
            earlier = by_witness[k, "nearest_commit_before_latch"]
            later = by_witness[k, "nearest_commit_after_latch"]
            if earlier.get("matches_latch_same_basis"):
                counts_here["matching_prior_witness"] += 1
                best = earlier
                prior_shape_counts[best["change_shape"]] += 1
                assert best["matches_latch_current_code"] is True
            elif later.get("matches_latch_same_basis"):
                counts_here["only_later_matching_witness"] += 1
                best = later
            else:
                counts_here["neither_nearest_witness_matches"] += 1
                best = None
            if best:
                shape_counts[best["change_shape"]] += 1
        rebuilt = {"n": len(cohort), **dict(counts_here), "best_matching_change_shape": dict(shape_counts)}
        assert rebuilt == read("supporting_sources.json")["witness_qualification"][label]
        qualifications[label] = {**rebuilt, "prior_matching_change_shape": dict(prior_shape_counts)}
    versions = read("benchmark_versions.json")
    assert len(versions) == 38 and all(v["columns"] == ["close", "volume"] and v["valid_open_rows"] == 0 for v in versions)
    action = read("supporting_sources.json")["corporate_action_metadata"]
    assert not ({"ex_date", "adjustment_factor", "split_factor", "distribution_ratio"} & set(action["columns"]))
    assert all(case["causal_attribution"] == "UNVERIFIED" for case in read("supporting_sources.json")["representative_cases"])
    leads = read("action_title_leads.json")
    lead_issuers = {row["sec_code"] for row in leads}
    changed_mature_issuers = {ticker.split(".")[0] for _, ticker in changed & mature}
    assert len(leads) == action["related_title_rows"] == 58
    assert len(lead_issuers) == action["changed_entry_issuers_with_action_title"] == 42
    assert len(lead_issuers & changed_mature_issuers) == action["mature_v4_changed_issuers_with_action_title"] == 13
    checks.append({"name": "all 1618 witness rows and exact bounded-clock classes independently reconstructed", "status": "PASS", "qualifications": qualifications, "source_limit": "All output-to-input identity links checked; this local replay does not reread all 3360 historical Git blobs or independently verify their ancestry."})

    # Unmodified producer APIs, deliberately discriminating synthetic inputs.
    source_receipt = {"sha256": "a" * 64, "clock_kind": "producer_available_at", "available_at": "2026-10-09T08:00:00Z", "fixture_only": True}
    def mark(ticker, session, anchor, bar):
        return contract.mark_from_bar(ticker=ticker, session=session, anchor=anchor, bar=bar, source=source_receipt, basis_id="synthetic-" + str(ticker) + "-v1")
    entry = mark("SYNTHETIC.SZ", "2026-09-16", "session_open", {"open": 100, "high": 102, "low": 99, "close": 101})
    leave = mark("SYNTHETIC.SZ", "2026-09-29", "session_close", {"close": 110})
    bench_entry = mark("SYNTHETIC_BENCH", "2026-09-16", "session_open", {"open": 200, "high": 202, "low": 199, "close": 201})
    bench_exit = mark("SYNTHETIC_BENCH", "2026-09-29", "session_close", {"close": 220})
    clocks = {"published_at": "2026-09-15T08:00:00Z", "entry_anchor_at": "2026-09-16T01:30:00Z", "graded_at": "2026-10-09T08:01:00Z"}

    def attempt(name, operation):
        try:
            value = operation()
            result = {"name": name, "outcome": "ACCEPTED", "result": value}
        except Exception as exc:
            result = {"name": name, "outcome": "REFUSED_OR_FAILED", "exception": type(exc).__name__, "reason": str(exc)}
        return result

    temporal = []
    future_leave, future_bench_exit = copy.deepcopy(leave), copy.deepcopy(bench_exit)
    future_leave["session"] = future_bench_exit["session"] = "2026-10-12"
    temporal.append(attempt("exit after grading admitted with an earlier source-availability string", lambda: contract.aligned_excess(entry, future_leave, bench_entry, future_bench_exit, **clocks)))
    temporal.append(attempt("late publication admitted using an unrelated later entry_anchor_at", lambda: contract.aligned_excess(entry, leave, bench_entry, bench_exit, **{**clocks, "published_at": "2026-10-01T08:00:00Z", "entry_anchor_at": "2026-10-02T01:30:00Z"})))
    bad_entry, bad_bench = copy.deepcopy(entry), copy.deepcopy(bench_entry)
    bad_entry["session"] = bad_bench["session"] = "2026-09-31"
    next_leave, next_bench_exit = copy.deepcopy(leave), copy.deepcopy(bench_exit)
    next_leave["session"] = next_bench_exit["session"] = "2026-10-01"
    temporal.append(attempt("nonexistent session date passes lexical session ordering", lambda: contract.aligned_excess(bad_entry, next_leave, bad_bench, next_bench_exit, **clocks)))
    assert all(t["outcome"] == "ACCEPTED" for t in temporal)
    findings.append({"id": "V1", "severity": "BLOCKER_FOR_CONTRACT_HANDOFF", "title": "Session and publication clocks are not bound to graded mark endpoints", "source": "fill_vintage_contract.py:validate_mark/aligned_excess", "counterexamples": temporal, "minimal_fix": "Require a calendar-owned anchor receipt linked to exact market/session/anchor; validate canonical session dates, entry and exit anchor ordering, publication <= actual entry anchor, and grading >= actual exit anchor. Validate source availability against the endpoint it contains. Add exit_anchor_at or a resolver/receipt covering both endpoints; do not trust an unrelated free timestamp."})

    original = contract.seal_event({"kind": "original_entry", "decision_id": "synthetic-decision-001", "ticker": "SYNTHETIC.SZ", "entry_session": "2026-09-16", "price": 100, "basis": "t1_open", "recorded_at": "2026-09-16T08:00:00Z"})
    ledger = contract.append_event([], original)
    tampered_ledger = copy.deepcopy(ledger)
    tampered_ledger[0]["price"] = 80
    replay = contract.append_event(tampered_ledger, original)
    assert replay[0]["price"] == 80 and replay[0]["event_id"] == original["event_id"]
    correction = contract.seal_event({"kind": "entry_correction", "decision_id": "synthetic-decision-001", "ticker": "SYNTHETIC.SZ", "entry_session": "2026-09-16", "price": 90, "basis": "t1_open", "correction_of": original["event_id"], "reason": "Synthetic correction", "recorded_at": "2026-10-09T08:00:00Z"})
    amended_corrupt = contract.append_event(tampered_ledger, correction)
    assert amended_corrupt[0]["price"] == 80 and len(amended_corrupt) == 2
    shifted = contract.seal_event({**{k: v for k, v in original.items() if k != "event_id"}, "entry_session": "2026-09-17", "price": 80})
    two_originals = contract.append_event(ledger, shifted)
    assert len(two_originals) == 2 and all(row["kind"] == "original_entry" for row in two_originals)
    findings.append({"id": "V2", "severity": "BLOCKER_FOR_CONTRACT_HANDOFF", "title": "Existing original records are not authenticated before replay or amendment", "source": "fill_vintage_contract.py:append_event", "counterexamples": [{"name": "stored original price changed 100 to 80 while event_id remained original", "outcome": "ACCEPTED", "replayed_original": replay[0]}, {"name": "correction accepted against the same tampered original", "outcome": "ACCEPTED", "ledger": amended_corrupt}, {"name": "same decision/ticker gets a second original by changing entry_session", "outcome": "ACCEPTED", "ledger": two_originals}], "minimal_fix": "Verify every prior record's digest, permitted kind and original-key uniqueness before replay or correction lookup. Bind the original to the incumbent decision/latch identity (stable board decision plus ticker), with entry_session a protected original field; a different session requires a separate correction. Require store-level immutable-original custody at persistence."})

    index = pd.DatetimeIndex(["2026-09-16", "2026-09-17"])
    frame = pd.DataFrame({"Open": [4.8, 4.85], "High": [4.9, 4.95], "Low": [4.7, 4.8], "Close": [4.85, 4.9], "Volume": [100.0, 101.0]}, index=index)
    corrupt = frame.copy()
    corrupt.loc[index[0], "Open"] = 9
    retained, diagnostic = benchmark.retain_optional_ohlcv(corrupt, "510300.SS")
    assert diagnostic["opening_mark_refusals"] == [{"session": "2026-09-16", "reason": "OPEN_OUTSIDE_RANGE"}]
    retained_bar = {k: float(v) for k, v in retained.loc[index[0]].items()}
    corrupt_entry = mark("SYNTHETIC_BENCH", "2026-09-16", "session_open", retained_bar)
    accepted_corrupt = contract.aligned_excess(entry, leave, corrupt_entry, bench_exit, **clocks)
    altered = copy.deepcopy(entry)
    altered["price"] = 80
    accepted_altered = contract.aligned_excess(altered, leave, bench_entry, bench_exit, **clocks)
    assert accepted_corrupt["status"] == accepted_altered["status"] == "ALIGNED_MARK_DIAGNOSTIC"
    findings.append({"id": "V3", "severity": "BLOCKER_FOR_CONTRACT_HANDOFF", "title": "Opening-mark refusal and bar-row identity do not reach the comparator", "source": "fill_vintage_contract.py:mark_from_bar/validate_mark; benchmark_retention_probe.py:retain_optional_ohlcv", "counterexamples": [{"name": "shim refuses open 9 outside range 4.7 to 4.9, constructor and comparator still admit it", "retention_diagnostic": diagnostic, "constructed_mark": corrupt_entry, "result": accepted_corrupt}, {"name": "mark price changed 100 to 80 without changing source or bar-row hash", "bar_row_hash_unchanged": entry["bar_row_sha256"] == altered["bar_row_sha256"], "result": accepted_altered}], "minimal_fix": "Make validated OHLC/range status part of the mark-admission contract, and require exact source-blob/row/field/anchor binding. Preserve bad observations while refusing derived opening marks. Recompute or verify the retained row identity rather than accepting an unchecked hash string."})

    node = next(n for n in ast.walk(ast.parse(source.decode())) if isinstance(n, ast.FunctionDef) and n.name == "_extract")
    namespace = {"pd": pd, "log": logging.getLogger("independent_vintage_review")}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "pinned_benchmark_extract", "exec"), namespace)
    incumbent = namespace["_extract"]
    optional_results = []
    for label, column, value in [("numeric string open", "Open", "4.8"), ("nonnumeric open token", "Open", "vendor-missing"), ("nonnumeric high token", "High", "vendor-missing")]:
        malformed = frame.copy()
        malformed[column] = malformed[column].astype(object)
        malformed.loc[index[0], column] = value
        old = incumbent(None, malformed, "510300.SS")
        pd.testing.assert_frame_equal(old, frame[["Close", "Volume"]].rename(columns={"Close": "close", "Volume": "volume"}))
        result = attempt(label, lambda: benchmark.retain_optional_ohlcv(malformed, "510300.SS"))
        assert result["outcome"] == "REFUSED_OR_FAILED" and result["exception"] == "TypeError"
        optional_results.append({**result, "incumbent_close_volume": "ACCEPTED_UNCHANGED", "original_optional_value": value})
    for label, shape in [("missing Volume", frame.drop(columns=["Volume"])), ("all Close missing", frame.assign(Close=float("nan"))), ("empty frame", frame.iloc[:0])]:
        assert incumbent(None, shape, "510300.SS") is None
        result, details = benchmark.retain_optional_ohlcv(shape, "510300.SS")
        assert result is None
        checks.append({"name": "backward compatibility control: " + label, "status": "PASS", "diagnostic": details})
    missing_optional = frame.assign(Open=float("nan"), High=float("nan"), Low=float("nan"))
    retained_missing, refused_missing = benchmark.retain_optional_ohlcv(missing_optional, "510300.SS")
    pd.testing.assert_frame_equal(retained_missing[["close", "volume"]], incumbent(None, missing_optional, "510300.SS"))
    assert refused_missing["qualified_open_rows"] == 0
    checks.append({"name": "all optional values missing preserve incumbent close/volume observations", "status": "PASS"})
    findings.append({"id": "V4", "severity": "BLOCKER_FOR_BACKWARD_COMPATIBLE_RETENTION", "title": "Malformed optional OHLC aborts a frame whose incumbent Close/Volume is usable", "source": "benchmark_retention_probe.py:retain_optional_ohlcv", "counterexamples": optional_results, "minimal_fix": "Type-check optional scalars before np.isfinite or comparisons. Keep original observed values, emit an explicit opening-mark refusal, and return the unchanged required Close/Volume projection. Decide explicitly whether numeric strings are refused or parsed under a named policy; optional data must not break existing consumers."})

    nonpositive = []
    old_bar = {"open": 100, "high": 102, "low": 98, "close": 101}
    for factor in [0, -0.8]:
        new_bar = {k: v * factor for k, v in old_bar.items()}
        observed = classify_bar(old_bar, new_bar)
        assert observed == "uniform_ohlc_scale"
        nonpositive.append({"factor": factor, "observed_class": observed})
    findings.append({"id": "V5", "severity": "MINOR_GUARD_GAP_NO_RETAINED_DATA_IMPACT", "title": "Shape classifier accepts zero and negative common scale", "source": "collect_vintage_evidence.py:classify_bar", "counterexamples": nonpositive, "minimal_fix": "Require finite positive new OHLC/ratios before naming a positive common scale. All retained actual uniform-scale witnesses independently pass positivity; no published denominator changes."})

    for name, identity in initial["files"].items():
        assert sha((LAB / name).read_bytes()) == identity["sha256"], "reviewed input changed during review: " + name
    checks.append({"name": "no producer file changed during review", "status": "PASS"})
    result = {"status": "REVIEW_COMPLETE_WITH_CONTRACT_BLOCKERS", "study_pin": PIN, "review_scope": "Research facts accepted; these pure prototypes require the listed contract corrections before an implementation handoff can treat their guards as complete. No claim of production failure, economic P&L certification or live execution is made.", "reviewed_manifest_sha256": initial["files"]["VINTAGE_MANIFEST.json"]["sha256"], "producer_reproduction": {"contract_checks": 18, "benchmark_checks": 9, "exact_result_replay": True}, "checks": checks, "independent_check_count": len(checks), "counts": counts, "witness_qualifications": qualifications, "v4_accounting": accounting, "aggregate_mean_change_pp": math.fsum(stats["contribution_to_289_row_mean_difference_pp"] for stats in accounting.values()), "sign_changes": {"total": sum(stats["win_sign_changes"] for stats in accounting.values()), "win_to_loss": sum(stats["original_win_to_current_loss"] for stats in accounting.values()), "loss_to_win": sum(stats["original_loss_to_current_win"] for stats in accounting.values())}, "findings": findings, "blocker_count": 4, "minor_count": 1, "limits": ["2632 and 933 aggregate episode-row totals remain tied to the hash-bound prior CSV; this review independently recounts the directly retained unique-entry and V4 episode rows.", "No original-latch production mutation, production imports, vendor calls, history fetches, or canonical PR writes occurred.", "Matching historical bars prove recoverable repository content, not availability to the original decision or execution. Action titles are leads without adjustment factors.", "Counterexamples are wholly synthetic and demonstrate contract-admission gaps; they do not relabel the retained empirical witnesses or adjust published returns."]}
    (HERE / "vintage_review_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "producer_checks_replayed": 27, "independent_checks": len(checks), "blockers": 4, "minor": 1, "out": str(HERE / "vintage_review_results.json")}))


if __name__ == "__main__":
    main()
