#!/usr/bin/env python3
"""B0_SYNTHETIC_SCALE — synthetic software-capacity benchmark for Market Memory.

Frozen protocol (SYNTHETIC_SOFTWARE_CAPACITY_ONLY, run mm-b0-synthetic-scale-
20261015-01a1333c-v1): sizes 16/64/128/256 captures, 5 trials per size, one
fresh subprocess of this same script per trial (OS page cache left warm),
corpus built once per size from the existing trusted-capture test fixtures,
then measured in a fresh process: owner pin re-read by the native owner, whole
pinned-generation cohort read, cohort disclosure, final-capture query feature
read, k=8 historical_hypothetical (purge=0, embargo=0) retrieval, retrieval
disclosure.  A negative check appends a 257th capture once to the already
measured 256 corpus and requires the unchanged MAX_CAPTURES=256 whole-generation
bound refusal before any retrieval can accept it.

Constraints honoured by construction:
  * New harness only. No repository/source/production mutation, no network,
    no credentials, no real data. Output goes exclusively into a NEW caller
    supplied absolute --output-dir (an existing path is refused), with the size
    corpora kept in their own subdirectories.
  * Capture/owner/load and Policy helpers are the exact existing test helpers,
    imported after --repo is inserted into sys.path.  The only monkeypatching
    anywhere is the fixture helper's own normal clock patch, performed inside
    the supplied capture() helper and driven through a plain pytest.MonkeyPatch
    instance.  This script never patches policy, capability, guard or limit
    code, and never writes to the repo (bytecode writing is disabled).
  * No performance claims are made beyond the measured runs recorded here;
    synthetic fixture cases are not real-world evidence and are never
    extrapolated into distributions beyond the reported nearest-rank P50/P95.
  * Query identity is the final capture's query_id/subject_id only; no bearer
    token, capability object or sealed body is ever persisted.
  * Per-process cap: 300 seconds wall clock per child, enforced by the parent;
    after a failure or timeout the remaining larger sizes are stopped and the
    gaps are reported.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # never add __pycache__ to the repo under test

import argparse
import json
import math
import os
import platform
import resource
import subprocess
import time
import traceback
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

RUN_ID = "mm-b0-synthetic-scale-20261015-01a1333c-v1"
SCHEMA = "b0.synthetic_scale.benchmark.v1"
KIND = "SYNTHETIC_SOFTWARE_CAPACITY_ONLY"
SIZES = (16, 64, 128, 256)
TRIALS_PER_SIZE = 5
K = 8
DATE_END = "2026-08-19"
QUERY_CUTOFF = "2026-08-20T12:00:00Z"
METHOD_SPEC = (0, 0, "historical_hypothetical")  # purge=0, embargo=0, fixed L1 baseline
PER_PROCESS_LIMIT_SECONDS = 300.0
CORPORA_DIRNAME = "corpora"
TRIALS_DIRNAME = "trials"
QUERY_META_NAME = "query_meta.json"
FIXTURE_NAME = "fixture-house-output.json"
REFUSAL_EXPECTED_MESSAGE = "whole_generation_capture_bound_exceeded"


class UsageError(Exception):
    """Caller-supplied inputs refused."""


# --------------------------------------------------------------------------- io


def write_private(path: Path, data: bytes) -> None:
    """Create a new regular file, mode 0600, no overwrite, no symlink."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
    finally:
        os.close(fd)


def dump_private(path: Path, obj: object) -> None:
    write_private(path, json.dumps(obj, separators=(",", ":")).encode("utf-8") + b"\n")


def sha256_file(path: Path) -> str:
    digest = sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def peak_rss_self() -> dict:
    """Platform-correct peak RSS for this process (Linux KiB vs macOS bytes)."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        nbytes = int(raw)  # macOS: bytes
    else:
        nbytes = int(raw) * 1024  # Linux (and BSD convention): kibibytes
    return {"raw": int(raw), "platform": sys.platform,
            "bytes": nbytes, "mib": round(nbytes / (1 << 20), 3)}


def nearest_rank(values: list[float], percentile: float) -> float:
    """Nearest-rank percentile: ceil(p/100 * n), 1-indexed, on sorted values."""
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile / 100.0 * len(ordered)))
    return ordered[rank - 1]


# ------------------------------------------------------------------- fixtures


def growth(i: int) -> float:
    """Deterministic bounded growth score for fixture capture index i."""
    return round(((i * 37 + 13) % 89) / 89.0 * 0.9, 4)


def session_for(i: int, n: int) -> str:
    """Consecutive calendar sessions ending 2026-08-19 (protocol date_end)."""
    return (date(2026, 8, 19) - timedelta(days=n - 1 - i)).isoformat()


def corpus_stats(root: Path) -> dict:
    """Logical file bytes/counts: source fixture vs retained store artifacts."""
    fixture = {"files": 0, "logical_bytes": 0}
    artifacts = {"files": 0, "logical_bytes": 0}
    metadata = {"files": 0, "logical_bytes": 0}
    for current, _dirs, names in os.walk(root):
        for name in names:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            size = path.stat().st_size
            bucket = fixture if rel == FIXTURE_NAME else metadata if rel == QUERY_META_NAME else artifacts
            bucket["files"] += 1
            bucket["logical_bytes"] += size
    total = {"files": fixture["files"] + artifacts["files"] + metadata["files"],
             "logical_bytes": fixture["logical_bytes"] + artifacts["logical_bytes"] + metadata["logical_bytes"]}
    return {"source_fixture": fixture, "retained_artifacts": artifacts, "harness_metadata": metadata, "total": total}


# ------------------------------------------------------------ repo helpers


class Modules:
    """Exact existing engine + test helper modules, imported from --repo."""


def load_repo_modules(repo: Path) -> Modules:
    marker = repo / "engine" / "neuralweb" / "market_memory_retained_context_cohort.py"
    if not marker.is_file():
        raise UsageError(f"--repo does not contain {marker}")
    sys.path.insert(0, str(repo))
    mods = Modules()
    from engine.neuralweb import market_memory as _mm
    from engine.neuralweb import market_memory_episode_comparison as _comparison
    from engine.neuralweb import market_memory_episode_features as _features
    from engine.neuralweb import market_memory_episode_retrieval as _retrieval
    from engine.neuralweb import market_memory_identity as _identity
    from engine.neuralweb import market_memory_pit as _pit
    from engine.neuralweb import market_memory_projection as _projection
    from engine.neuralweb import market_memory_retained_context_cohort as _cohort
    from engine.neuralweb import market_memory_trusted as _trusted
    from tests import test_market_memory_episode_features as _features_tests
    from tests import test_market_memory_episode_retrieval as _retrieval_tests
    from tests import test_market_memory_retained_context_cohort as _cohort_tests
    from tests import test_market_memory_trusted as _trusted_tests
    mods.mm, mods.features, mods.comparison = _mm, _features, _comparison
    mods.retrieval, mods.identity, mods.pit = _retrieval, _identity, _pit
    mods.projection, mods.cohort, mods.trusted = _projection, _cohort, _trusted
    mods.features_tests, mods.retrieval_tests = _features_tests, _retrieval_tests
    mods.cohort_tests, mods.trusted_tests = _cohort_tests, _trusted_tests
    mods.capture = _cohort_tests.capture
    mods.owner = _cohort_tests.owner
    mods.CUTOFF = _cohort_tests.CUTOFF
    mods.Policy = _features_tests.Policy
    return mods


def source_hashes(mods: Modules, repo: Path, script: Path) -> dict:
    entries = {}
    for name in ("mm", "features", "comparison", "retrieval", "identity", "pit",
                 "projection", "cohort", "trusted"):
        module = getattr(mods, name)
        rel = os.path.relpath(module.__file__, repo)
        entries[rel] = sha256_file(Path(module.__file__))
    for name in ("cohort_tests", "trusted_tests", "features_tests", "retrieval_tests"):
        module = getattr(mods, name)
        rel = os.path.relpath(module.__file__, repo)
        entries[rel] = sha256_file(Path(module.__file__))
    entries["<harness>/benchmark.py"] = sha256_file(script)
    return dict(sorted(entries.items()))


def observed_constants(mods: Modules) -> dict:
    return {"cohort_MAX_CAPTURES": mods.cohort.MAX_CAPTURES,
            "cohort_MAX_OWNER_BYTES": mods.cohort.MAX_OWNER_BYTES,
            "cohort_MAX_MANIFEST_BYTES": mods.cohort.MAX_MANIFEST_BYTES,
            "retrieval_MAX_K": mods.retrieval.MAX_K,
            "retrieval_MAX_RESULT_BYTES": mods.retrieval.MAX_RESULT_BYTES,
            "cohort_schema": mods.cohort.SCHEMA,
            "retrieval_schema": mods.retrieval.SCHEMA}


def identity_fingerprint(mods: Modules) -> dict:
    return {"cohort_sha256": sha256_file(Path(mods.cohort.__file__)),
            "retrieval_sha256": sha256_file(Path(mods.retrieval.__file__)),
            "features_sha256": sha256_file(Path(mods.features.__file__)),
            "cohort_MAX_CAPTURES": mods.cohort.MAX_CAPTURES}


def git_head(repo: Path):
    """Best-effort local read-only HEAD lookup; never required."""
    try:
        done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                              capture_output=True, text=True, timeout=5)
    except Exception:
        return None
    if done.returncode == 0:
        return done.stdout.strip() or None
    return None


# ---------------------------------------------------------------- child modes


def child_trial(args, mods: Modules) -> int:
    corpus = Path(args.corpus_dir)
    meta = json.loads((corpus / QUERY_META_NAME).read_bytes())
    size = int(args.size)
    if meta.get("size") != size:
        raise UsageError("query_meta size mismatch")
    subject_id, query_id = meta["subject_id"], meta["query_id"]
    result_path = Path(args.result)

    phases = {}
    clock = time.perf_counter
    reader_pin_start = clock()
    reader, pin = mods.owner(corpus)  # native owner re-reads the pin itself
    phases["owner_pin"] = round(clock() - reader_pin_start, 6)

    cohort_start = clock()
    population = mods.cohort.read_retained_context_cohort(
        reader, pin, subject_id=subject_id, query_cutoff=mods.CUTOFF,
        policy=mods.Policy())
    phases["cohort_read"] = round(clock() - cohort_start, 6)

    cohort_disclose_start = clock()
    cohort_value = mods.cohort.disclose_retained_context_cohort(
        population, policy=mods.Policy())
    phases["cohort_disclose"] = round(clock() - cohort_disclose_start, 6)

    query_start = clock()
    query_cap = mods.features.read_episode_feature_capability(
        reader, pin, query_id=query_id, subject_id=subject_id,
        query_cutoff=mods.CUTOFF, policy=mods.Policy())
    phases["query_feature_read"] = round(clock() - query_start, 6)

    method = mods.retrieval.RetainedContextMethodSpec(*METHOD_SPEC)
    retrieve_start = clock()
    retrieval_cap = mods.retrieval.retrieve_retained_contexts(
        population, query_cap, policy=mods.Policy(), k=K, method=method)
    phases["retrieve"] = round(clock() - retrieve_start, 6)

    disclose_start = clock()
    retrieval_value = mods.retrieval.disclose_episode_retrieval(
        retrieval_cap, policy=mods.Policy())
    phases["retrieve_disclose"] = round(clock() - disclose_start, 6)

    denominator = retrieval_value["denominator"]
    counts = cohort_value["counts"]
    expected_returned = min(K, size - 1)
    validation = {
        "expected_capture_count": cohort_value["expected_capture_count"],
        "cohort_row_count": len(cohort_value["rows"]),
        "counts_sum": sum(counts.values()),
        "counts": counts,
        "denominator": denominator,
        "retrieval_status": retrieval_value["status"],
        "membership_sha256": cohort_value["membership_sha256"],
        "selection_sha256": retrieval_value["selection_sha256"],
        "returned_context_ids": [row["candidate"]["context_id"]
                                 for row in retrieval_value["selected"]],
    }
    ok = (validation["expected_capture_count"] == size
          and validation["cohort_row_count"] == size
          and validation["counts_sum"] == size
          and denominator["expected_captures"] == size
          and denominator["accounted_captures"] == size
          and denominator["eligible_representatives"] == size - 1
          and denominator["returned"] == expected_returned
          and retrieval_value["status"] == "MATCHES")
    result = {"ok": ok, "mode": "trial", "size": size, "phases": phases,
              "total_measured_seconds": round(sum(phases.values()), 6),
              "peak_rss": peak_rss_self(),
              "validation": validation,
              "identity": identity_fingerprint(mods),
              "method_spec": {"purge_calendar_days": METHOD_SPEC[0],
                              "embargo_calendar_days": METHOD_SPEC[1],
                              "mode": METHOD_SPEC[2], "k": K},
              "query_identity": {"query_id": query_id, "subject_id": subject_id,
                                 "note": "final capture identifiers only; no "
                                         "capability or bearer persisted"}}
    dump_private(result_path, result)
    print(json.dumps({"mode": "trial", "ok": ok, "size": size},
                     separators=(",", ":")))
    return 0 if ok else 1


def child_refusal(args, mods: Modules) -> int:
    corpus = Path(args.corpus_dir)
    meta = json.loads((corpus / QUERY_META_NAME).read_bytes())
    result_path = Path(args.result)
    reader, pin = mods.owner(corpus)
    captures = len(pin.captures)
    max_captures = mods.cohort.MAX_CAPTURES
    retrieval_attempted = False
    refusal = None
    capability_returned = False
    try:
        mods.cohort.read_retained_context_cohort(
            reader, pin, subject_id=meta["subject_id"],
            query_cutoff=mods.CUTOFF, policy=mods.Policy())
        capability_returned = True
    except mods.cohort.RetainedContextCohortError as exc:
        refusal = {"error_type": type(exc).__name__,
                   "raised_in_module": type(exc).__module__,
                   "message": str(exc),
                   "matches_whole_generation":
                       str(exc) == REFUSAL_EXPECTED_MESSAGE}
    ok = (refusal is not None and refusal["matches_whole_generation"]
          and captures == max_captures + 1 and max_captures == 256)
    result = {"ok": ok, "mode": "refusal_257",
              "captures_in_generation": captures,
              "MAX_CAPTURES_observed": max_captures,
              "refusal": refusal,
              "retrieval_attempted": retrieval_attempted,
              "capability_returned": capability_returned,
              "no_false_acceptance": ok and not capability_returned}
    dump_private(result_path, result)
    print(json.dumps({"mode": "refusal_257", "ok": ok, "captures": captures},
                     separators=(",", ":")))
    return 0 if ok else 1


# ---------------------------------------------------------------- parent mode


def build_corpus(mods: Modules, corpus_dir: Path, size: int) -> dict:
    """Build one size corpus once with the exact existing capture() fixtures.

    All clock adjustments are the fixture helper's own normal monkeypatch,
    applied inside capture() through a plain pytest.MonkeyPatch instance.
    """
    if os.path.lexists(corpus_dir):
        raise RuntimeError(f"refusing existing corpus directory {corpus_dir}")
    os.makedirs(corpus_dir, mode=0o700)
    start = time.perf_counter()
    monkeypatch = pytest.MonkeyPatch()
    try:
        last = None
        fixture_writes = 0
        for index in range(size):
            last = mods.capture(corpus_dir, monkeypatch,
                                session=session_for(index, size),
                                growth=growth(index))
            fixture_writes += 1
            (corpus_dir / FIXTURE_NAME).stat().st_size  # source fixture present
    finally:
        monkeypatch.undo()
    build_seconds = time.perf_counter() - start
    meta = {"size": size, "subject_id": last.packet["subject"]["subject_id"],
            "query_id": last.capture_receipt["query_id"],
            "date_end": DATE_END, "query_is_final_capture": True,
            "growth_pattern": "round(((i*37+13) % 89)/89*0.9, 4)"}
    dump_private(corpus_dir / QUERY_META_NAME, meta)
    return {"corpus_dir": str(corpus_dir), "build_seconds": round(build_seconds, 6),
            "build_mean_seconds_per_capture": round(build_seconds / size, 6),
            "source_fixture_writes": fixture_writes,
            "corpus": corpus_stats(corpus_dir),
            "query_identity": {"query_id": meta["query_id"],
                               "subject_id": meta["subject_id"],
                               "query_is_final_capture": True}}


def child_build(args, mods: Modules) -> int:
    result = build_corpus(mods, Path(args.corpus_dir), int(args.size))
    dump_private(Path(args.result), result)
    return 0


def child_append(args, mods: Modules) -> int:
    start = time.perf_counter()
    patch = pytest.MonkeyPatch()
    try:
        capture = mods.capture(Path(args.corpus_dir), patch, session=DATE_END,
                               growth=growth(256), seconds=3600)
        result = {"append_seconds": round(time.perf_counter() - start, 6),
                  "appended_capture": {"query_id": capture.capture_receipt["query_id"],
                                       "subject_id": capture.packet["subject"]["subject_id"]}}
    finally:
        patch.undo()
    dump_private(Path(args.result), result)
    return 0


def run_child(script: Path, repo: Path, child_args: list[str],
              env: dict) -> dict:
    """Run one fresh subprocess of this script under the 300s per-process cap."""
    command = [sys.executable, str(script), "--repo", str(repo)] + child_args
    start = time.perf_counter()
    try:
        done = subprocess.run(command, capture_output=True, text=True,
                              env=env, timeout=PER_PROCESS_LIMIT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        return {"timeout": True, "wall_seconds": round(time.perf_counter() - start, 6),
                "stdout_tail": (exc.stdout or "")[-800:] if isinstance(exc.stdout, str) else "",
                "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else ""}
    return {"timeout": False, "returncode": done.returncode,
            "wall_seconds": round(time.perf_counter() - start, 6),
            "stdout_tail": done.stdout[-800:], "stderr_tail": done.stderr[-2000:]}


def phase_percentiles(records: list[dict]) -> dict:
    phases = sorted({name for record in records for name in record["phases"]})
    percentiles = {}
    for name in phases + ["total_measured_seconds"]:
        key = name if name == "total_measured_seconds" else None
        values = [record["phases"][name] for record in records if name in record["phases"]] \
            if key is None else [record["total_measured_seconds"] for record in records]
        if not values:
            continue
        percentiles[name] = {"n": len(values),
                             "p50_s": round(nearest_rank(values, 50), 6),
                             "p95_s": round(nearest_rank(values, 95), 6)}
    rss_values = [record["peak_rss"]["bytes"] for record in records]
    percentiles["peak_rss"] = {"n": len(rss_values), "platform_corrected_unit": "bytes",
                               "p50_bytes": nearest_rank(rss_values, 50),
                               "p95_bytes": nearest_rank(rss_values, 95),
                               "p50_mib": round(nearest_rank(rss_values, 50) / (1 << 20), 3),
                               "p95_mib": round(nearest_rank(rss_values, 95) / (1 << 20), 3)}
    return percentiles


def run_size(mods: Modules, script: Path, repo: Path, out_dir: Path,
             size: int, env: dict) -> tuple[dict, list[dict]]:
    """Build one corpus, run 5 fresh-process trials, aggregate P50/P95."""
    gaps: list[dict] = []
    trials_dir = out_dir / TRIALS_DIRNAME / f"size_{size}"
    os.makedirs(trials_dir, mode=0o700)
    build_path = trials_dir / "build.json"
    outcome = run_child(script, repo,
                        ["--child-build", "--corpus-dir",
                         str(out_dir / CORPORA_DIRNAME / f"size_{size}"),
                         "--size", str(size), "--result", str(build_path)], env)
    if outcome["timeout"] or outcome.get("returncode") != 0 or not build_path.is_file():
        return {"size": size, "status": "build_failed", "process": outcome}, [
            {"scope": f"build:size_{size}", "class": "build_error",
             "detail": outcome}]
    build = json.loads(build_path.read_bytes())
    build["build_process_wall_seconds"] = outcome["wall_seconds"]
    report = {"size": size, "status": "ok", **build, "trials": []}
    expected_returned = min(K, size - 1)
    for trial in range(1, TRIALS_PER_SIZE + 1):
        result_path = trials_dir / f"trial_{trial}.json"
        outcome = run_child(script, repo,
                            ["--child-trial", "--corpus-dir", build["corpus_dir"],
                             "--size", str(size), "--result", str(result_path)], env)
        if outcome["timeout"]:
            report["status"] = "trial_timeout"
            gaps.append({"scope": f"trial:size_{size}:{trial}", "class": "timeout",
                         "detail": f"child exceeded {PER_PROCESS_LIMIT_SECONDS}s",
                         "child_stderr_tail": outcome["stderr_tail"]})
            break
        record = None
        if outcome["returncode"] == 0 and os.path.exists(result_path):
            try:
                record = json.loads(result_path.read_bytes())
            except Exception as exc:
                gaps.append({"scope": f"trial:size_{size}:{trial}",
                             "class": "result_unreadable",
                             "detail": f"{type(exc).__name__}: {exc}"})
        if record is None:
            report["status"] = "trial_failed"
            gaps.append({"scope": f"trial:size_{size}:{trial}",
                         "class": "child_failure",
                         "detail": f"exit={outcome['returncode']}",
                         "child_stdout_tail": outcome["stdout_tail"],
                         "child_stderr_tail": outcome["stderr_tail"]})
            break
        validation = record.get("validation", {})
        checks = (record.get("ok") is True
                  and validation.get("expected_capture_count") == size
                  and validation.get("counts_sum") == size
                  and validation.get("denominator", {}).get("expected_captures") == size
                  and validation.get("denominator", {}).get("accounted_captures") == size
                  and validation.get("denominator", {}).get("eligible_representatives") == size - 1
                  and validation.get("denominator", {}).get("returned") == expected_returned
                  and validation.get("retrieval_status") == "MATCHES"
                  and record.get("identity") == identity_fingerprint(mods))
        if not checks:
            report["status"] = "validation_failed"
            gaps.append({"scope": f"trial:size_{size}:{trial}",
                         "class": "validation_mismatch",
                         "detail": json.dumps(validation, sort_keys=True)[:1200],
                         "child_stderr_tail": outcome["stderr_tail"]})
            break
        report["trials"].append({
            "trial": trial, "ok": True,
            "process_wall_seconds": outcome["wall_seconds"],
            "phases": record["phases"],
            "total_measured_seconds": record["total_measured_seconds"],
            "peak_rss": record["peak_rss"],
            "selection_sha256": validation["selection_sha256"],
            "membership_sha256": validation["membership_sha256"],
            "denominator": validation["denominator"]})
    else:
        selections = {trial["selection_sha256"] for trial in report["trials"]}
        memberships = {trial["membership_sha256"] for trial in report["trials"]}
        report["determinism"] = {
            "single_selection_across_trials": len(selections) == 1,
            "single_membership_across_trials": len(memberships) == 1,
            "selection_sha256": (selections.pop() if len(selections) == 1 else sorted(selections)),
            "membership_sha256": (memberships.pop() if len(memberships) == 1 else sorted(memberships))}
        if not (report["determinism"]["single_selection_across_trials"]
                and report["determinism"]["single_membership_across_trials"]):
            report["status"] = "determinism_failed"
            gaps.append({"scope": f"size_{size}", "class": "determinism_mismatch",
                         "detail": "selection or membership digests differ across trials"})
    if report["status"] == "ok":
        report["percentiles"] = phase_percentiles(report["trials"])
    return report, gaps


def run_refusal(mods: Modules, script: Path, repo: Path, out_dir: Path,
                env: dict) -> tuple[dict, list[dict]]:
    """Append capture #257 once to the measured 256 corpus; require refusal."""
    corpus_dir = out_dir / CORPORA_DIRNAME / "size_256"
    meta_path = corpus_dir / QUERY_META_NAME
    if not meta_path.is_file():
        return {"status": "skipped",
                "detail": "256-capture corpus unavailable; negative check not run"}, [
            {"scope": "negative_257", "class": "skipped",
             "detail": "size-256 corpus was not built (earlier failure)"}]
    gaps: list[dict] = []
    append_path = out_dir / "negative_257_append.json"
    append_outcome = run_child(script, repo,
                              ["--child-append", "--corpus-dir", str(corpus_dir),
                               "--result", str(append_path)], env)
    if (append_outcome["timeout"] or append_outcome.get("returncode") != 0
            or not append_path.is_file()):
        return {"status": "append_failed", "process": append_outcome}, [
            {"scope": "negative_257", "class": "append_error", "detail": append_outcome}]
    report = {"status": "ran", "corpus_dir": str(corpus_dir),
              **json.loads(append_path.read_bytes()),
              "note": "appended once after all size-256 trials; measured state had 256 captures"}
    result_path = out_dir / "negative_257_result.json"
    outcome = run_child(script, repo,
                        ["--child-refusal", "--corpus-dir", str(corpus_dir),
                         "--result", str(result_path)], env)
    report["process_wall_seconds"] = outcome["wall_seconds"]
    if outcome["timeout"]:
        report["status"] = "timeout"
        gaps.append({"scope": "negative_257", "class": "timeout",
                     "detail": f"child exceeded {PER_PROCESS_LIMIT_SECONDS}s",
                     "child_stderr_tail": outcome["stderr_tail"]})
        return report, gaps
    record = None
    if outcome["returncode"] == 0 and os.path.exists(result_path):
        record = json.loads(result_path.read_bytes())
    if record is None:
        report["status"] = "failed"
        gaps.append({"scope": "negative_257", "class": "child_failure",
                     "detail": f"exit={outcome['returncode']}",
                     "child_stdout_tail": outcome["stdout_tail"],
                     "child_stderr_tail": outcome["stderr_tail"]})
        return report, gaps
    report["child_result"] = record
    report["status"] = "refused" if record.get("ok") else "not_refused"
    if report["status"] != "refused":
        gaps.append({"scope": "negative_257", "class": "refusal_missing",
                     "detail": json.dumps(record.get("refusal"), sort_keys=True)})
    return report, gaps


def parent_main(args) -> int:
    if not args.output_dir:
        raise UsageError("--output-dir is required for the benchmark run")
    script = Path(__file__).resolve()
    repo = Path(args.repo).expanduser().resolve()
    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        raise UsageError("--output-dir must be an absolute path")
    if os.path.lexists(out_dir):
        raise UsageError(f"--output-dir already exists: {out_dir}")
    mods = load_repo_modules(repo)
    os.makedirs(out_dir, mode=0o700)
    os.makedirs(out_dir / CORPORA_DIRNAME, mode=0o700)
    os.makedirs(out_dir / TRIALS_DIRNAME, mode=0o700)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"

    initial_hashes = source_hashes(mods, repo, script)
    sizes_report: list[dict] = []
    gaps: list[dict] = []
    stopped_after = None
    for size in SIZES:
        if stopped_after is not None:
            gaps.append({"scope": f"size_{size}", "class": "skipped_after_failure",
                         "detail": f"stopped after failure at size {stopped_after}"})
            continue
        report, size_gaps = run_size(mods, script, repo, out_dir, size, env)
        sizes_report.append(report)
        gaps.extend(size_gaps)
        if report["status"] != "ok":
            stopped_after = size
    negative_report, negative_gaps = run_refusal(mods, script, repo, out_dir, env)
    gaps.extend(negative_gaps)

    final_hashes = source_hashes(mods, repo, script)
    if final_hashes != initial_hashes:
        gaps.append({"scope": "source", "class": "source_changed_during_measurement"})
    complete = (stopped_after is None and not gaps
                and negative_report["status"] == "refused")
    summary = {
        "schema": SCHEMA, "run_id": RUN_ID, "kind": KIND,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repo": str(repo), "source_head_git_best_effort": git_head(repo),
        "harness_sha256": sha256_file(script),
        "python": sys.version.split()[0], "platform": platform.platform(),
        "protocol": {"sizes": list(SIZES), "trials_per_size": TRIALS_PER_SIZE,
                     "fresh_process_each_trial": True,
                     "warm_cache_policy": "OS page cache not cleared; corpus "
                                          "build time reported separately from "
                                          "fresh-process query time",
                     "date_end": DATE_END, "query_cutoff": QUERY_CUTOFF, "k": K,
                     "method": "historical_hypothetical purge=0 embargo=0 fixed L1",
                     "method_spec": {"purge_calendar_days": METHOD_SPEC[0],
                                     "embargo_calendar_days": METHOD_SPEC[1],
                                     "mode": METHOD_SPEC[2]},
                     "policy": "existing tests Policy fake authorizer; not "
                               "production authorization cost",
                     "per_process_limit_seconds": PER_PROCESS_LIMIT_SECONDS},
        "source_hashes_sha256": initial_hashes,
        "source_hashes_unchanged_after_run": final_hashes == initial_hashes,
        "observed_constants": observed_constants(mods),
        "sizes": sizes_report,
        "negative_check_257": negative_report,
        "gaps": gaps,
        "measurement_scope": {
            "synthetic_fixtures_not_real_evidence": True,
            "no_production_data_or_service_reads": True,
            "no_repository_or_source_mutation": True,
            "no_network_or_provider_calls": True,
            "no_limit_guard_or_policy_monkeypatch": True,
            "no_extrapolation_beyond_measured_runs": True,
            "policy_is_test_fake_authorizer": True},
        "status": "complete" if complete else "completed_with_gaps"}
    dump_private(out_dir / "summary.json", summary)
    compact = {"run_id": RUN_ID, "status": summary["status"],
               "sizes": {str(report["size"]): {
                   "status": report["status"],
                   "build_s": report.get("build_seconds"),
                   "total_p50_s": (report.get("percentiles", {})
                                    .get("total_measured_seconds", {}).get("p50_s")),
                   "total_p95_s": (report.get("percentiles", {})
                                    .get("total_measured_seconds", {}).get("p95_s")),
                   "rss_p95_mib": (report.get("percentiles", {})
                                    .get("peak_rss", {}).get("p95_mib"))}
                   for report in sizes_report},
               "negative_257": negative_report["status"],
               "gaps": len(gaps), "summary": str(out_dir / "summary.json")}
    print(json.dumps(compact, separators=(",", ":")))
    return 0 if complete else 1


# ----------------------------------------------------------------------- cli


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="B0 synthetic software-capacity scale benchmark "
                    "(Market Memory retained-context cohort + retrieval)")
    parser.add_argument("--repo", required=True,
                        help="absolute path to the repository root to place on sys.path")
    parser.add_argument("--output-dir",
                        help="NEW absolute output directory; refused if it exists "
                             "(parent mode only)")
    parser.add_argument("--child-build", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--child-append", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--child-trial", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--child-refusal", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--corpus-dir", help=argparse.SUPPRESS)
    parser.add_argument("--size", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--result", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv) -> int:
    args = parse_args(argv)
    modes = [name for name in ("child_trial", "child_refusal", "child_build", "child_append") if getattr(args, name)]
    if len(modes) > 1:
        print("refusing combined child modes", file=sys.stderr)
        return 2
    try:
        if modes:
            mods = load_repo_modules(Path(args.repo).expanduser().resolve())
            if not (args.corpus_dir and args.result):
                raise UsageError("child mode requires --corpus-dir and --result")
            return globals()[modes[0]](args, mods)
        return parent_main(args)
    except UsageError as exc:
        print(f"usage_error: {exc}", file=sys.stderr)
        return 2
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
